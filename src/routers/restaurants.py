# Router des restaurants : lecture publique (liste et détail) et
# modification réservée à l'admin (infos de contact et ouverture).
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core import require_role
from src.db.database import get_db
from src.models import Restaurant, User

router = APIRouter()


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
@router.get("/restaurants", response_model=list[RestaurantOut])
def get_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()


# GET /restaurants/{restaurant_id} : détail d'un restaurant (public), 404 s'il n'existe pas
@router.get("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
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
@router.patch("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def patch_restaurant(item: RestaurantUpdate, restaurant_id: int, db: Session = Depends(get_db),
                     admin: User = Depends(require_role("admin"))):
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
@router.patch("/restaurants/{restaurant_id}/availability", response_model=RestaurantOut)
def patch_restaurant_availability(item: RestaurantAvailability, restaurant_id: int, db: Session = Depends(get_db),
                                  admin: User = Depends(require_role("admin"))):
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
@router.post("/restaurants", status_code=201, response_model=RestaurantOut)
def create_restaurant(item: RestaurantCreate, db: Session = Depends(get_db),
                      admin: User = Depends(require_role("admin"))):
    # Le nom sert de clé au seed : il doit rester unique
    if db.query(Restaurant).filter_by(name=item.name).first():
        raise HTTPException(status_code=400, detail="Un restaurant porte déjà ce nom")

    # model_dump + ** : les champs du schéma ont exactement les noms des colonnes
    nouveau_restaurant = Restaurant(**item.model_dump())
    db.add(nouveau_restaurant)
    db.commit()
    db.refresh(nouveau_restaurant)  # récupère l'id généré
    return nouveau_restaurant