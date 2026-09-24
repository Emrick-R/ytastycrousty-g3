# Router des restaurants : lecture publique (liste et détail) et
# modification réservée à l'admin (infos de contact et ouverture).
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core import require_role, REPONSES_LECTURE, REPONSES_ECRITURE, REPONSES_CREATION
from src.db.database import get_db
from src.models import Restaurant, User

router = APIRouter(tags=["Restaurants"])


# Schéma de sortie : ce que l'API renvoie pour un restaurant
class RestaurantOut(BaseModel):
    id: int
    name: str
    city: str
    address: str
    is_open: bool
    opening_hours: str
    contact: str


# GET /restaurants : liste de tous les restaurants (public)
@router.get("/restaurants", response_model=list[RestaurantOut], summary="Lister les restaurants")
def get_restaurants(db: Session = Depends(get_db)):
    """
    Liste les trois restaurants avec leurs horaires, contact et état d'ouverture. Public.
    """
    return db.query(Restaurant).all()


# GET /restaurants/{restaurant_id} : détail d'un restaurant (public), 404 s'il n'existe pas
@router.get("/restaurants/{restaurant_id}", response_model=RestaurantOut, responses=REPONSES_LECTURE,
            summary="Consulter un restaurant")
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """
    Détail d'un restaurant. Public. **404** s'il n'existe pas.
    """
    restaurant = db.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return restaurant


# Schéma d'entrée du PATCH : champs optionnels pour une mise à jour partielle.
# name, city et is_open volontairement absents (name sert de clé au seed,
# is_open a son propre endpoint).
class RestaurantUpdate(BaseModel):
    address: str | None = None
    contact: str | None = None


# PATCH /restaurants/{restaurant_id} : modifie adresse et/ou contact (admin uniquement)
@router.patch("/restaurants/{restaurant_id}", response_model=RestaurantOut, responses=REPONSES_ECRITURE,
              summary="Modifier un restaurant")
def patch_restaurant(item: RestaurantUpdate, restaurant_id: int, db: Session = Depends(get_db),
                     admin: User = Depends(require_role("admin"))):
    """
        Modifie l'**adresse** et/ou le **contact**. Réservé à l'**admin**.

        Seuls les champs envoyés sont modifiés. L'ouverture se change via `/availability`.
        """
    restaurant = db.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ressource introuvable")

    if item.address is not None:
        restaurant.address = item.address
    if item.contact is not None:
        restaurant.contact = item.contact

    db.commit()
    db.refresh(restaurant)
    return restaurant


# Schéma d'entrée de l'availability : is_open obligatoire (422 si absent)
class RestaurantAvailability(BaseModel):
    is_open: bool


# PATCH /restaurants/{restaurant_id}/availability : ouvre ou ferme un restaurant (admin uniquement).
# Idempotent : renvoyer le même état redonne simplement 200.
@router.patch("/restaurants/{restaurant_id}/availability", response_model=RestaurantOut, responses=REPONSES_ECRITURE,
              summary="Ouvrir ou fermer un restaurant")
def patch_restaurant_availability(item: RestaurantAvailability, restaurant_id: int, db: Session = Depends(get_db),
                                  admin: User = Depends(require_role("admin"))):
    """
        Passe le restaurant en ouvert (`true`) ou fermé (`false`). Réservé à l'**admin**.

        Un restaurant fermé refuse les nouvelles commandes. Renvoyer le même état redonne **200**.
        """
    restaurant = db.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    restaurant.is_open = item.is_open

    db.commit()
    db.refresh(restaurant)
    return restaurant


# Schéma d'entrée du POST
class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1)
    city: str = Field(min_length=1)
    address: str
    is_open: bool = True  # ouvert par défaut, comme dans le modèle
    opening_hours: str
    contact: str


# POST /restaurant : créer un restaurant (admin uniquement).
@router.post("/restaurants", status_code=201, response_model=RestaurantOut, responses=REPONSES_CREATION,
             summary="Créer un restaurant")
def create_restaurant(item: RestaurantCreate, db: Session = Depends(get_db),
                      admin: User = Depends(require_role("admin"))):
    """
        Ajoute un restaurant. Réservé à l'**admin** (route bonus, non exigée par le contrat).

        Le nom doit être unique (**400** sinon). Ouvert par défaut.
        """
    # Le nom sert de clé au seed : il doit rester unique
    if db.query(Restaurant).filter_by(name=item.name).first():
        raise HTTPException(status_code=400, detail="Un restaurant porte déjà ce nom")

    # model_dump + ** : les champs du schéma ont exactement les noms des colonnes
    nouveau_restaurant = Restaurant(**item.model_dump())
    db.add(nouveau_restaurant)
    db.commit()
    db.refresh(nouveau_restaurant)  # récupère l'id généré
    return nouveau_restaurant
