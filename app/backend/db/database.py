from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = PROJECT_ROOT / "var" / "dashboard"
DB_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DB_DIR / "blog_publisher.db"
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "BLOG_PUBLISHER_DB_URL", f"sqlite:///{DEFAULT_DB_PATH}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
