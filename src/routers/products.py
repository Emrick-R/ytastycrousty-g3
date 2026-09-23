# Router des produits : lecture publique de la carte (avec filtres), et
# création/modification/suppression soumises à l'autorisation par restaurant.
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from src.core import get_current_user, verifier_acces_restaurant
from src.models import Produit, User, Restaurant
from src.db.database import get_db

router = APIRouter()


# Schéma de sortie : ce que l'API renvoie pour un produit
class ProductOut(BaseModel):
    id: int
    name: str
    image: str
    description: str
    category: str
    # float : le Decimal renvoyé par Numeric est converti en nombre JSON simple (9.9 et non "9.90")
    price: float
    is_available: bool
    restaurant_id: int
    ingredients: list[str]


# GET /products : category, q, restaurant_id, is_available
@router.get("/products", response_model=list[ProductOut])
def products(db: Session = Depends(get_db),
             category: str | None = None,
             q: str | None = None,
             is_available: bool | None = None,
             restaurant_id: int | None = None
             ):
    query = db.query(Produit)
    if category is not None:
        query = query.filter(Produit.category == category)
    if q is not None:
        # or_ : le produit est gardé si AU MOINS UNE des conditions est vraie
        query = query.filter(or_(
            Produit.name.ilike(f"%{q}%"),
            Produit.description.ilike(f"%{q}%"),
            # func : appelle une fonction SQL de Postgres ; array_to_string colle les éléments
            # de la liste en un seul texte (["pain", "poulet"] -> "pain,poulet") pour pouvoir y chercher
            func.array_to_string(Produit.ingredients, ",").ilike(f"%{q}%"),
        ))
    if is_available is not None:
        query = query.filter(Produit.is_available == is_available)
    if restaurant_id is not None:
        query = query.filter(Produit.restaurant_id == restaurant_id)
    produits = query.all()
    return produits


# GET /products/{product_id}
@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    produit = db.query(Produit).filter_by(id=product_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return produit


# Schéma d'entrée de la création d'un produit
class ProductCreate(BaseModel):
    name: str = Field(min_length=1)  # nom non vide
    image: str
    description: str
    category: str = Field(min_length=1)  # catégorie non vide (sert aux filtres)
    price: float = Field(gt=0)  # gt=0 : strictement positif, sinon 422
    is_available: bool = True  # disponible par défaut s'il n'est pas précisé
    restaurant_id: int
    ingredients: list[str] = []  # liste vide acceptée si non envoyée


# POST /products : création d'un produit (admin partout, staff dans son restaurant)
@router.post("/products", status_code=201, response_model=ProductOut)
def create_product(item: ProductCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    # 403 si l'utilisateur n'a pas le droit d'agir sur ce restaurant
    verifier_acces_restaurant(user, item.restaurant_id)

    # 400 si le restaurant n'existe pas (sinon la clé étrangère provoquerait une 500)
    if not db.query(Restaurant).filter_by(id=item.restaurant_id).first():
        raise HTTPException(status_code=400, detail="Restaurant inexistant")

    # model_dump : convertit le schéma Pydantic en dictionnaire, déballé ensuite avec **
    produit = Produit(**item.model_dump())
    db.add(produit)
    db.commit()
    db.refresh(produit)  # récupère l'id généré
    return produit


# Schéma d'entrée du PATCH : champs optionnels pour une mise à jour partielle.
# restaurant_id volontairement absent (un produit ne change pas de restaurant),
# is_available aussi (endpoint dédié /availability).
class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    image: str | None = None
    description: str | None = None
    category: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    ingredients: list[str] | None = None


# Schéma d'entrée de l'availability : is_available obligatoire (422 si absent)
class ProductAvailability(BaseModel):
    is_available: bool


# Charge un produit ou lève un 404 : évite de répéter ces lignes dans les trois routes
def charger_produit(db: Session, product_id: int) -> Produit:
    produit = db.query(Produit).filter_by(id=product_id).first()
    if not produit:
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return produit


# PATCH /products/{product_id} : mise à jour partielle (admin partout, staff dans son restaurant)
@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, item: ProductUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    produit = charger_produit(db, product_id)
    # Accès vérifié contre le restaurant DU PRODUIT EN BASE, jamais contre le body
    verifier_acces_restaurant(user, produit.restaurant_id)

    if item.name is not None:
        produit.name = item.name
    if item.image is not None:
        produit.image = item.image
    if item.description is not None:
        produit.description = item.description
    if item.category is not None:
        produit.category = item.category
    if item.price is not None:
        produit.price = item.price
    if item.ingredients is not None:
        produit.ingredients = item.ingredients

    db.commit()
    db.refresh(produit)
    return produit


# DELETE /products/{product_id} : suppression (admin partout, staff dans son restaurant), 204 sans contenu
@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    produit = charger_produit(db, product_id)
    verifier_acces_restaurant(user, produit.restaurant_id)

    # Un produit déjà commandé ne peut pas être supprimé : ses lignes de commande
    # pointent vers lui (clé étrangère), et on ne veut pas effacer l'historique des commandes
    if produit.order_items:
        raise HTTPException(status_code=400,
                            detail="Produit présent dans des commandes : rendez-le indisponible plutôt que de le supprimer")

    db.delete(produit)
    db.commit()


# PATCH /products/{product_id}/availability : rend un produit disponible ou non.
# Idempotent : renvoyer le même état redonne simplement 200.
@router.patch("/products/{product_id}/availability", response_model=ProductOut)
def update_product_availability(product_id: int, item: ProductAvailability, db: Session = Depends(get_db),
                                user: User = Depends(get_current_user)):
    produit = charger_produit(db, product_id)
    verifier_acces_restaurant(user, produit.restaurant_id)

    produit.is_available = item.is_available
    db.commit()
    db.refresh(produit)
    return produit
