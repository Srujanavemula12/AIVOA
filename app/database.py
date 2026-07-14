"""
Database configuration.

Defaults to local SQLite for zero-friction local development / demo recording.
To use Postgres or MySQL instead (as the assignment spec allows), just set
DATABASE_URL in your .env file, e.g.:

    DATABASE_URL=postgresql://user:password@localhost:5432/aivoa_crm
    DATABASE_URL=mysql+pymysql://user:password@localhost:3306/aivoa_crm

No code changes needed - SQLAlchemy handles the dialect switch.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aivoa_crm.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
