from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db


app = FastAPI(
    title="Aasra API",
    description="Backend API for Aasra",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Aasra API is running"
    }


@app.get("/test-db")
def test_database(db: Session = Depends(get_db)):

    result = db.execute(text("SELECT 1"))

    return {
        "database": "connected",
        "result": result.scalar()
    }

@app.get("/users")
def get_users(db: Session = Depends(get_db)):

    result = db.execute(
        text("SELECT * FROM public.users")
    )

    users = result.mappings().all()

    return users