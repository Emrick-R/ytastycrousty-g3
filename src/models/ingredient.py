from sqlalchemy import Integer, Column, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base

# Pas besoin de faire une nouvelle classe, car il n'y a que des FK donc on fait directe une Table
produit_ingredient = Table(
    "produit_ingredient",
    Base.metadata, # Declare la table directement a la db au meme titre que les classe sous (Base)
    Column("produit_id", Integer, ForeignKey("produits.id"), primary_key=True),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id"), primary_key=True)
)

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    produits = relationship("Produit", secondary="produit_ingredient", back_populates="ingredients")