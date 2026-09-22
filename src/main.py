# pour lancer le serveur : uv run uvicorn src.main:app --reload
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.db.database import Base, engine, SessionLocal
from src.models.user import User
from src.core.security import hashing_mdp


# asynccontextmanager permet de lancer des fonctions au lancement de l'app et à sa fermeture.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage
    Base.metadata.create_all(bind=engine)
    try :
        db = SessionLocal()
        adm = db.query(User).filter_by(username="admin123").first()
        if not adm:
            db.add(User(
                first_name="Admin",
                last_name="Ytasty",
                username="admin123",
                hashed_password=hashing_mdp("Admin@123456"),
                role="admin"
            ))
            db.commit()
    finally:
        db.close()

    yield
    # A la fermeture

app = FastAPI(title="ytastycrousty-g3", lifespan=lifespan)

# route health, renvoi status ok si le server est allumé
@app.get("/health")
def health():
    return {"status": "ok"}