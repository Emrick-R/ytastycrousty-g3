# Modèle SQLAlchemy de la table "order_item".
from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, Column, String, Numeric, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from src.db.database import Base

# "items": [
#   {
#     "product_id": 10,
#     "quantity": 2
#   }
# ]

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    quantity =  Column(Integer, nullable=False)
    # le prix est figé au moment de la commande et servira à faire le calcul du prix total.
    prix_fige_commande = Column(Numeric(4,2), nullable=False)

    product_id = Column(Integer, ForeignKey("produits.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))

    produit = relationship("Produit", back_populates="order_items")
    order = relationship("Order", back_populates="order_items")