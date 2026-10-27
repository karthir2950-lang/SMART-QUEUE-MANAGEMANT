import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

def init_engine():
    # If DATABASE_URL is PostgreSQL, test connection with a short timeout
    if settings.DATABASE_URL and not settings.DATABASE_URL.startswith("sqlite"):
        try:
            from sqlalchemy.pool import NullPool
            pg_engine = create_engine(
                settings.DATABASE_URL,
                poolclass=NullPool,
                connect_args={"connect_timeout": 10}
            )
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("INFO: Connected to PostgreSQL database.")
            return pg_engine
        except Exception as e:
            print(f"WARNING: PostgreSQL database connection failed ({e}). Falling back to local SQLite database.")

    # SQLite fallback
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sqlite_path = os.path.join(backend_dir, "smart_queue.db")
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    return sqlite_engine

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def get_db():
    if not SessionLocal:
        raise Exception("Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auto-initialize schema & seed ONLY if SQLite is used
try:
    if engine and engine.dialect.name == "sqlite":
        from app.models.domain import User, Sector, Organization, Branch, Service, Counter, Staff, Appointment, QueueToken, QueueEvent
        Base.metadata.create_all(bind=engine)
        from app.db.seed import seed_db
        init_db = SessionLocal()
        try:
            seed_db(init_db)
        finally:
            init_db.close()
except Exception as seed_err:
    print(f"INFO: Database initialization notice: {seed_err}")
