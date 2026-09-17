# Modèle SQLAlchemy de la table "users", liée à un restaurant.
from sqlalchemy import Integer, Column, String, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

# {
#   "first_name": "Alice",
#   "last_name": "Martin",
#   "username": "alice123",
#   "password": "Secure@12345",
#   "role": "staff",
#   "restaurant_id": 1
# }

class User(Base):
    __tablename__="users"
    id = Column(Integer, primary_key=True)  # id	identifiant unique (clé primaire)
    first_name = Column (String, nullable=False)
    last_name = Column (String, nullable=False)
    username = Column (String, nullable=False)
    hashed_password = Column (String, nullable=False) # Attention c'est un mdp hashé
    role =Column (String, nullable=False)
    restaurant_id = Column (Integer, ForeignKey("restaurants.id"))
    restaurant = relationship("Restaurant", back_populates="users")