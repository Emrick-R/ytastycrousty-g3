# Modèle SQLAlchemy de la table "produit".
from sqlalchemy import Integer, Column, String, Boolean, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from src.db.database import Base

# {
#   "name": "Burger Test",
#   "image": "https://example.com/burger.jpg",
#   "description": "Produit créé pour les tests",
#   "category": "burgers",
#   "price": 9.9,
#   "is_available": true,
#   "restaurant_id": 1,
#   "ingredients": ["pain", "poulet"]
# }

class Produit(Base):
    __tablename__ = "produits"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    image = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    # Numeric(6,2) : 6 chiffres dont 2 après la virgule, jusqu'à 9999.99
    price = Column(Numeric(6, 2), nullable=False)
    is_available = Column(Boolean, default=True)
    # ARRAY(String) : type PostgreSQL qui stocke une liste de textes dans une seule colonne
    ingredients = Column(ARRAY(String), nullable=False)

    # Obligatoire : un produit appartient toujours à un restaurant (base de l'autorisation par restaurant)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    restaurant = relationship("Restaurant", back_populates="produits")
    order_items = relationship("OrderItem", back_populates="produit")