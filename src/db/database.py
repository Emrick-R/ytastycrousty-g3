# Connexion SQLAlchemy à PostgreSQL : engine, session par requête, et Base pour les modèles.
import os
from sqlalchemy import create_engine, Column, Integer, Boolean, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ytastyg3:ytastyg3@127.0.0.1:5432/ytastyg3",  # fallback pour dev local hors Docker
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # classe de base dont hériteront tous les modèles (S2, juste après)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()