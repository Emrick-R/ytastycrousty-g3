# pour lancer le serveur : uv run uvicorn src.main:app --reload
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.db.seed import seed_admin, seed_restaurant, seed_produits, seed_utilisateurs
from src.db.database import Base, engine, SessionLocal

from src.routers.auth import router as auth_router
from src.routers.restaurants import router as restaurant_router
from src.routers.products import router as produit_router


# asynccontextmanager permet de lancer des fonctions au lancement de l'app et à sa fermeture.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed du compte admin
        seed_admin(db)
        seed_restaurant(db)
        seed_produits(db)
        seed_utilisateurs(db)
    finally:
        db.close()

    yield
    # A la fermeture


app = FastAPI(title="ytastycrousty-g3", lifespan=lifespan)

# Route /auth
app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(produit_router)


# route health, renvoi status ok si le server est allumé
@app.get("/health")
def health():
    return {"status": "ok"}
