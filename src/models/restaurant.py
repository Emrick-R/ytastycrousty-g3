# Modèle SQLAlchemy de la table "restaurants".
from sqlalchemy import Integer, Column, String, Boolean
from sqlalchemy.orm import relationship
from src.db.database import Base

# Option	        Rôle
# nullable=False	Interdit les valeurs vides — le champ devient obligatoire
# default=valeur	Valeur utilisée automatiquement si rien n'est fourni à la création

class Restaurant(Base):
    __tablename__ = "restaurants"
    id =Column(Integer, primary_key=True) # id	identifiant unique (clé primaire)
    name = Column(String, nullable=False) # name	nom du restaurant
    city = Column(String, nullable=False) # city	ville
    address = Column(String, nullable=False) # address	adresse complète
    is_open = Column(Boolean, default=True) # is_open	booléen — resto ouvert ou fermé
    opening_hours = Column(String, nullable=False) # opening_hours	horaires d'ouverture
    contact = Column(String, nullable=False) # contact	téléphone ou email de contact

    users = relationship("User", back_populates="restaurant")
    produits = relationship("Produit", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
