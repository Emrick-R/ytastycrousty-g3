# pour lancer le serveur : uv run uvicorn src.main:app --reload
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.database import Base, engine
import src.models

# asynccontextmanager permet de lancer des fonctions au lancement de l'app et à sa fermeture.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage
    Base.metadata.create_all(bind=engine)
    yield
    # A la fermeture

app = FastAPI(title="ytastycrousty-g3", lifespan=lifespan)

# route health, renvoi status ok si le server est allumé
@app.get("/health")
def health():
    return {"status": "ok"}