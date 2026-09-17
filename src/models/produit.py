# Modèle SQLAlchemy de la table "produit".
from sqlalchemy import Integer, Column, String, Boolean, Numeric, ForeignKey
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
    price = Column(Numeric(4,2), nullable=False)
    is_available = Column(Boolean, default=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    restaurant = relationship("Restaurant", back_populates="produits")
    ingredients = relationship("Ingredient", secondary="produit_ingredient", back_populates="produits")

