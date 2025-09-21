from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./education_db.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def init_db():
    from app.db.models import chat, documents, qa, training
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")