from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import (
    auth, patients, medications, reminders, games, mood, movement,
    memory_lane, emergency, sync, dashboard, home,
)

app = FastAPI(
    title="Aasra API",
    description="Backend API for Aasra — a daily-assistance app for elderly dementia patients and their caregivers.",
    version="1.0.0",
)

# Flutter Web runs in Chrome from a localhost/127.0.0.1 origin and sends
# JSON/Authorization headers, which causes the browser to perform a CORS
# preflight request. Android does not enforce browser CORS, so this can make
# an API that works perfectly on the emulator fail only in Chrome.
#
# Keep this restricted to local development origins rather than using "*".
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
