import secrets
import string
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core import get_current_user, verifier_lecture_restaurant, verifier_acces_restaurant, REPONSES_LECTURE, \
    REPONSES_LECTURE_PROTEGEE, ERR_400, REPONSES_ECRITURE
from src.db.database import get_db
from src.models import User, Restaurant, Status, PickupMode, Order, Produit, OrderItem

router = APIRouter(tags=["Commandes"])


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    unit_price: float  # prix figé au moment de la commande


class CustomerOut(BaseModel):
    name: str
    email: str


class OrderOut(BaseModel):
    order_number: str
    restaurant_id: int
    created_at: datetime
    items: list[OrderItemOut]
    total_price: float
    status: Status
    pickup_mode: PickupMode
    customer: CustomerOut


def commande_vers_sortie(order: Order) -> OrderOut:
    # Traduit le modèle SQLAlchemy (client à plat, lignes dans order_items)
    # vers la forme du contrat (customer imbriqué, lignes dans items)
    return OrderOut(
        order_number=order.order_number,
        restaurant_id=order.restaurant_id,
        created_at=order.created_at,
        items=[
            OrderItemOut(product_id=i.product_id, quantity=i.quantity, unit_price=i.prix_fige_commande)
            for i in order.order_items
        ],
        total_price=order.total_price,
        status=order.status,
        pickup_mode=order.pickup_mode,
        customer=CustomerOut(name=order.customer_name, email=order.customer_email),
    )


def charger_commande(db: Session, order_number: str) -> Order:
    # Charge une commande par son numéro ou lève un 404
    order = db.query(Order).filter_by(order_number=order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return order


# GET /orders/{order_number} : suivi d'une commande par son numéro (public)
@router.get("/orders/{order_number}", response_model=OrderOut, responses=REPONSES_LECTURE,
            summary="Suivre une commande")
def get_order(order_number: str, db: Session = Depends(get_db)):
    """
    Consulte une commande à partir de son numéro de suivi. Public. **404** si le numéro est inconnu.
    """
    return commande_vers_sortie(charger_commande(db, order_number))


# GET /restaurants/{restaurant_id}/orders : commandes d'un restaurant, filtrables par statut
@router.get("/restaurants/{restaurant_id}/orders", response_model=list[OrderOut], responses=REPONSES_LECTURE_PROTEGEE,
            summary="Lister les commandes d'un restaurant")
def list_restaurant_orders(restaurant_id: int, status: Status | None = None,
                           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Commandes d'un restaurant, les plus récentes en premier, filtrables par `status`.

    - **admin** et **direction** : tous les restaurants
    - **staff** : uniquement son restaurant (**403** sinon)
    """
    # 404 si le restaurant n'existe pas, puis 403 si l'utilisateur ne peut pas le consulter
    if not db.query(Restaurant).filter_by(id=restaurant_id).first():
        raise HTTPException(status_code=404, detail="Restaurant introuvable")
    verifier_lecture_restaurant(user, restaurant_id)

    query = db.query(Order).filter(Order.restaurant_id == restaurant_id)
    if status is not None:
        query = query.filter(Order.status == status)
    # Les plus récentes en premier
    orders = query.order_by(Order.created_at.desc()).all()
    return [commande_vers_sortie(o) for o in orders]


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)  # quantité <= 0 refusée par le contrat -> 422


class CustomerIn(BaseModel):
    name: str = Field(min_length=1)
    # pattern : vérification simple du format email (texte@texte.texte)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OrderCreate(BaseModel):
    restaurant_id: int
    items: list[OrderItemIn] = Field(min_length=1)  # une commande vide n'a pas de sens
    pickup_mode: PickupMode  # Enum : toute autre valeur que onsite/takeaway -> 422
    customer: CustomerIn


ALPHABET = string.ascii_uppercase + string.digits  # A-Z et 0-9


def generer_order_number(db: Session) -> str:
    # secrets : tirage imprévisible (contrairement à random), car le numéro donne accès public à la commande
    while True:
        numero = "YC-" + "".join(secrets.choice(ALPHABET) for _ in range(8))
        # Collision quasi impossible (36^8 combinaisons), mais on vérifie quand même
        if not db.query(Order).filter_by(order_number=numero).first():
            return numero


# POST /orders : création d'une commande (public), total calculé côté serveur
@router.post("/orders", status_code=201, response_model=OrderOut, responses=ERR_400, summary="Passer une commande")
def create_order(item: OrderCreate, db: Session = Depends(get_db)):
    """
        Crée une commande et renvoie son **numéro de suivi** (`YC-XXXXXXXX`). Public.

        Le **prix total est calculé par le serveur** à partir des prix en base ;
        le prix de chaque produit est figé dans la commande.

        Commande refusée (**400**) si le restaurant est fermé ou inexistant, ou si un produit
        n'existe pas, appartient à un autre restaurant ou est indisponible.
        Quantité inférieure ou égale à 0 : **422**.
        """
    restaurant = db.query(Restaurant).filter_by(id=item.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=400, detail="Restaurant inexistant")
    if not restaurant.is_open:
        raise HTTPException(status_code=400, detail="Restaurant fermé")

    order_items = []
    total = Decimal("0")
    for ligne in item.items:
        produit = db.query(Produit).filter_by(id=ligne.product_id).first()
        if not produit:
            raise HTTPException(status_code=400, detail=f"Produit {ligne.product_id} inexistant")
        if produit.restaurant_id != item.restaurant_id:
            raise HTTPException(status_code=400, detail=f"Produit {ligne.product_id} d'un autre restaurant")
        if not produit.is_available:
            raise HTTPException(status_code=400, detail=f"Produit {ligne.product_id} indisponible")

        # Prix pris EN BASE, jamais dans la requête du client
        total += produit.price * ligne.quantity
        order_items.append(OrderItem(product_id=produit.id, quantity=ligne.quantity,
                                     prix_fige_commande=produit.price))

    order = Order(
        order_number=generer_order_number(db),
        restaurant_id=item.restaurant_id,
        total_price=total,
        pickup_mode=item.pickup_mode,
        customer_name=item.customer.name,
        customer_email=item.customer.email,
        order_items=order_items,  # les lignes sont enregistrées avec la commande via la relation
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return commande_vers_sortie(order)


# POST /orders/{order_number}/cancel : annulation (admin, ou staff du restaurant)
@router.post("/orders/{order_number}/cancel", response_model=OrderOut, responses=REPONSES_ECRITURE,
             summary="Annuler une commande")
def cancel_order(order_number: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
        Passe la commande au statut `cancelled`.

        **admin** partout, **staff** sur les commandes de son restaurant, **direction** refusée.
        Une commande déjà retirée (`collected`) ne peut plus être annulée (**400**).
        Annuler une commande déjà annulée redonne **200**.
        """
    order = charger_commande(db, order_number)
    # Écriture : verifier_acces_restaurant (direction refusée), pas la version lecture
    verifier_acces_restaurant(user, order.restaurant_id)

    if order.status == Status.collected:
        raise HTTPException(status_code=400, detail="Commande déjà retirée, annulation impossible")

    # Idempotent : annuler une commande déjà annulée renvoie simplement 200
    order.status = Status.cancelled
    db.commit()
    db.refresh(order)
    return commande_vers_sortie(order)


class OrderStatusUpdate(BaseModel):
    status: Status  # Enum : un statut hors liste -> 422


# Statuts finaux : une commande retirée ou annulée ne change plus de statut
STATUTS_FINAUX = (Status.collected, Status.cancelled)


# PATCH /orders/{order_number}/status : changement de statut (admin, ou staff du restaurant)
@router.patch("/orders/{order_number}/status", response_model=OrderOut, responses=REPONSES_ECRITURE,
              summary="Changer le statut d'une commande")
def update_order_status(order_number: str, item: OrderStatusUpdate, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """
    Statuts possibles : `pending`, `validated`, `preparing`, `ready`, `collected`, `cancelled`.

    **admin** partout, **staff** sur les commandes de son restaurant, **direction** refusée.
    Une commande `collected` ou `cancelled` ne change plus de statut (**400**).
    """
    order = charger_commande(db, order_number)
    # Écriture : verifier_acces_restaurant (direction refusée), pas la version lecture
    verifier_acces_restaurant(user, order.restaurant_id)

    # Une commande finale ne bouge plus, sauf si on renvoie le même statut (idempotence)
    if order.status in STATUTS_FINAUX and item.status != order.status:
        raise HTTPException(status_code=400, detail=f"Commande déjà {order.status.value}, statut non modifiable")

    order.status = item.status
    db.commit()
    db.refresh(order)
    return commande_vers_sortie(order)
