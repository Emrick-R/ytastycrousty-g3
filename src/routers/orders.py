from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core import get_current_user, verifier_lecture_restaurant
from src.db.database import get_db
from src.models import User, Restaurant, Status, PickupMode, Order

router = APIRouter()

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
@router.get("/orders/{order_number}", response_model=OrderOut)
def get_order(order_number: str, db: Session = Depends(get_db)):
    return commande_vers_sortie(charger_commande(db, order_number))


# GET /restaurants/{restaurant_id}/orders : commandes d'un restaurant, filtrables par statut
@router.get("/restaurants/{restaurant_id}/orders", response_model=list[OrderOut])
def list_restaurant_orders(restaurant_id: int, status: Status | None = None,
                           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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