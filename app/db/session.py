from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./education_db.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
def get_db():
    """FastAPI dependency: grąžina DB sesiją ir ją uždaro po užklausos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
def init_db():
    from app.db.base import Base
    from app.db import models
    
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")