# pour lancer le serveur : uv run uvicorn src.main:app --reload
from fastapi import FastAPI
from contextlib import asynccontextmanager

from pydantic import BaseModel

from src.db.seed import seed_admin, seed_restaurant, seed_produits, seed_utilisateurs
from src.db.database import Base, engine, SessionLocal

from src.routers.auth import router as auth_router
from src.routers.restaurants import router as restaurant_router
from src.routers.products import router as produit_router
from src.routers.orders import router as order_router


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


# Descriptions des sections de Swagger (une par tag de router)
TAGS_METADATA = [
    {"name": "Santé", "description": "Vérification que l'API répond."},
    {"name": "Auth & Users", "description": "Connexion JWT et gestion des comptes (création réservée à l'admin)."},
    {"name": "Restaurants", "description": "Consultation publique des restaurants ; modification réservée à l'admin."},
    {"name": "Produits",
     "description": "Carte des restaurants, filtrable. Écriture : admin partout, staff sur son restaurant."},
    {"name": "Commandes", "description": "Création et suivi publics ; gestion par le personnel du restaurant."},
]

app = FastAPI(title="Ytasty Crousty API - Groupe 3", lifespan=lifespan, version="1.0.0", openapi_tags=TAGS_METADATA,
              # description : texte d'accueil en Markdown affiché en haut de /docs
              description=(
                  "API de commande en ligne des restaurants Ytasty Crousty.\n\n"
                  "**Pour tester les routes protégées :**\n"
                  "1. `POST /auth/login` avec `admin123` / `Admin@123456`\n"
                  "2. Copier l'`access_token` de la réponse\n"
                  "3. Bouton **Authorize** en haut à droite, coller le token\n\n"
                  "**Rôles :** admin (tout), staff (écriture sur son restaurant), direction (lecture seule).\n\n\n"
                  "Réalisation par RIVET Emrick - étudiant IA & DATA B2 Sophia Ynov Campus"
              ),
              )

# Route /auth
app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(produit_router)
app.include_router(order_router)

# Schéma de sortie du health (format imposé par le contrat)
class HealthOut(BaseModel): status: str

# route health, renvoi status ok si le server est allumé
@app.get("/health", tags=["Santé"], summary="Vérifier que l'API répond", response_model=HealthOut)
def health():
    """
    Renvoie `{"status": "ok"}` si l'API est démarrée. Public.
    """
    return {"status": "ok"}
