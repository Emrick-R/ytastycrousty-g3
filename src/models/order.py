# Modèle SQLAlchemy de la table "order".
from datetime import datetime, timezone
import enum
from sqlalchemy import Integer, Column, String, Numeric, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from src.db.database import Base


# {
#   "order_number": "...",
#   "restaurant_id": 1,
#   "created_at": "...",
#   "items": [...],
#   "total_price": 19.80,
#   "status": "pending",
#   "pickup_mode": "takeaway",
#   "customer": {"name": "...", "email": "..."}
# }

# Statuts autorisés: pending, validated, preparing, ready, collected, cancelled
# str dit que par ex. Status.pending === "pending" => True
# enum.Enum permet de définir la classe python. / différend de Enum de SQLAlchemy qui permet de lier les enum py à sql
class Status(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    preparing = "preparing"
    ready = "ready"
    collected = "collected"
    cancelled = "cancelled"


# Modes de retrait: onsite, takeaway
class PickupMode(str, enum.Enum):
    onsite = "onsite"
    takeaway = "takeaway"


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)

    order_number = Column(String, nullable=False, unique=True)  # La commande peut être une suite de chiffre et de lettre
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # lanmda permet de créer une mini fonction qui s'utilise à chaque appel
    total_price = Column(Numeric(6, 2), nullable=False)  # Il peut aller jusqu'à 9999.99
    status = Column(Enum(Status), nullable=False)
    pickup_mode = Column(Enum(PickupMode), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)

    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))

    restaurant = relationship("Restaurant", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
