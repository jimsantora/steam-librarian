"""Core database connection and session management"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

# Get database path from environment or use default
DB_PATH = os.environ.get('STEAM_LIBRARY_DB', 'steam_library.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with performance optimizations
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
        "timeout": 30,
    },
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_database():
    """Create all tables in the database"""
    # Import all models to ensure they're registered with Base
    from src.models import game, user, review  # noqa
    Base.metadata.create_all(bind=engine)

def drop_database():
    """Drop all tables in the database"""
    Base.metadata.drop_all(bind=engine)

# Helper functions for common queries
def get_or_create(session: Session, model, **kwargs):
    """Get an existing instance or create a new one"""
    instance = session.query(model).filter_by(**kwargs).first()
    if not instance:
        instance = model(**kwargs)
        session.add(instance)
    return instance

def bulk_insert_or_update(session: Session, model, data_list, unique_fields):
    """Efficiently insert or update multiple records"""
    for data in data_list:
        filters = {field: data[field] for field in unique_fields if field in data}
        instance = session.query(model).filter_by(**filters).first()
        
        if instance:
            # Update existing
            for key, value in data.items():
                setattr(instance, key, value)
        else:
            # Insert new
            instance = model(**data)
            session.add(instance)
    
    session.commit()