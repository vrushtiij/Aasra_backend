from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, assert_can_access_patient
from app.services import summary as summary_service

router = APIRouter(tags=["cognitive-games"])


@router.get("/games", response_model=List[schemas.CognitiveGameOut])
def list_games(language: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.CognitiveGame).filter(models.CognitiveGame.active.is_(True))
    if language:
        q = q.filter(models.CognitiveGame.language == language)
    return q.all()


@router.post("/patients/{patient_id}/game-sessions", response_model=schemas.GameSessionOut, status_code=status.HTTP_201_CREATED)
def start_game_session(
    patient_id: str,
    body: schemas.GameSessionStart,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Starts a session. If no game_id is given (e.g. the morning 5-question
    check-in), picks the next adaptive game: the patient's own preferred
    language, easiest game type they haven't played recently, difficulty
    based on their latest accuracy."""
    assert_can_access_patient(patient_id, user, db)

    game = None
    if body.game_id:
        game = db.query(models.CognitiveGame).filter(models.CognitiveGame.game_id == body.game_id).first()
        if game is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    else:
        game = _pick_adaptive_game(patient_id, db)
        if game is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No active games configured")

    difficulty = body.difficulty or _suggest_difficulty(patient_id, db)

    session = models.GameSession(
        patient_id=patient_id,
        game_id=game.game_id,
        start_time=datetime.now(),
        difficulty=difficulty,
        completion_status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.put("/game-sessions/{session_id}/finish", response_model=schemas.GameSessionOut)
def finish_game_session(
    session_id: str,
    body: schemas.GameSessionFinish,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(models.GameSession).filter(models.GameSession.session_id == session_id).first()
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    assert_can_access_patient(session.patient_id, user, db)

    session.end_time = datetime.now()
    session.accuracy = body.accuracy
    session.score = body.score if body.score is not None else body.accuracy
    session.completion_status = body.completion_status
    db.flush()

    _update_progress(session.patient_id, session, db)
    if body.completion_status == "completed":
        summary_service.touch(session.patient_id, db, cognitive_game_completed=True)

    db.commit()
    db.refresh(session)
    return session


@router.get("/patients/{patient_id}/cognitive-progress", response_model=List[schemas.CognitiveProgressOut])
def get_progress(
    patient_id: str,
    days: int = 14,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(models.CognitiveProgress)
        .filter(models.CognitiveProgress.patient_id == patient_id, models.CognitiveProgress.date >= since)
        .order_by(models.CognitiveProgress.date)
        .all()
    )
    return rows


def _pick_adaptive_game(patient_id: str, db: Session) -> Optional[models.CognitiveGame]:
    profile = db.query(models.PatientProfile).filter(models.PatientProfile.patient_id == patient_id).first()
    language = profile.preferred_language if profile else None

    recent_game_ids = {
        s.game_id for s in (
            db.query(models.GameSession)
            .filter(models.GameSession.patient_id == patient_id)
            .order_by(models.GameSession.start_time.desc())
            .limit(3)
            .all()
        )
    }

    q = db.query(models.CognitiveGame).filter(models.CognitiveGame.active.is_(True))
    if language:
        q = q.filter(models.CognitiveGame.language == language)
    candidates = q.all()
    if not candidates:
        candidates = db.query(models.CognitiveGame).filter(models.CognitiveGame.active.is_(True)).all()

    fresh = [g for g in candidates if g.game_id not in recent_game_ids]
    pool = fresh or candidates
    return pool[0] if pool else None


def _suggest_difficulty(patient_id: str, db: Session) -> str:
    last = (
        db.query(models.GameSession)
        .filter(models.GameSession.patient_id == patient_id, models.GameSession.accuracy.isnot(None))
        .order_by(models.GameSession.start_time.desc())
        .first()
    )
    if last is None or last.accuracy is None:
        return "easy"
    if last.accuracy >= 85:
        return "hard"
    if last.accuracy >= 60:
        return "medium"
    return "easy"


def _update_progress(patient_id: str, session: models.GameSession, db: Session):
    """Rolls this session's accuracy into today's cognitive_progress row,
    scored against the game's type (memory/attention/recall/pattern)."""
    game = db.query(models.CognitiveGame).filter(models.CognitiveGame.game_id == session.game_id).first()
    today = date.today()
    row = (
        db.query(models.CognitiveProgress)
        .filter(models.CognitiveProgress.patient_id == patient_id, models.CognitiveProgress.date == today)
        .first()
    )
    if row is None:
        row = models.CognitiveProgress(patient_id=patient_id, date=today)
        db.add(row)
        db.flush()

    field_map = {
        "memory": "memory_score", "attention": "attention_score",
        "recall": "recall_score", "pattern": "pattern_score",
    }
    field = field_map.get(game.game_type if game else None)
    if field and session.accuracy is not None:
        setattr(row, field, session.accuracy)

    scores = [v for v in (row.memory_score, row.attention_score, row.recall_score, row.pattern_score) if v is not None]
    row.overall_score = sum(scores) / len(scores) if scores else None

    yesterday = today - timedelta(days=1)
    prev = (
        db.query(models.CognitiveProgress)
        .filter(models.CognitiveProgress.patient_id == patient_id, models.CognitiveProgress.date == yesterday)
        .first()
    )
    if prev and prev.overall_score is not None and row.overall_score is not None:
        diff = row.overall_score - prev.overall_score
        row.trend = "improving" if diff > 2 else "declining" if diff < -2 else "stable"
    db.flush()
