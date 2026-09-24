# Centralise l'import de tous les modèles pour que Base les enregistre (nécessaire à la création des tables).
from src.models.restaurant import Restaurant
from src.models.user import User
from src.models.produit import Produit
from src.models.order import Status, PickupMode, Order
from src.models.order_item import OrderItem

# Pour tester si les modèles se chargent bien dans le mapping SQLAlchemy :
# uv run python -c "import src.models; print('OK, modèles chargés')"