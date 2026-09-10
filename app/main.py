from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.firebase import init_firebase
from app.routers import (
    auth, patients, medications, reminders, games, mood, movement,
    memory_lane, emergency, sync, dashboard, home,
)

app = FastAPI(
    title="Aasra API",
    description="Backend API for Aasra — a daily-assistance app for elderly dementia patients and their caregivers.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    init_firebase()


@app.get("/")
def root():
    return {"message": "Aasra API is running"}


@app.get("/test-db")
def test_database(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {"database": "connected", "result": result.scalar()}


app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(medications.router)
app.include_router(reminders.router)
app.include_router(games.router)
app.include_router(mood.router)
app.include_router(movement.router)
app.include_router(memory_lane.router)
app.include_router(emergency.router)
app.include_router(sync.router)
app.include_router(dashboard.router)
app.include_router(home.router)
