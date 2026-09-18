# Centralise l'import de tous les modèles pour que Base les enregistre (nécessaire à la création des tables).
from src.models.restaurant import Restaurant
from src.models.user import User

# Centralise l'import de tous les modèles pour que Base les enregistre (nécessaire à la création des tables).
from src.models.restaurant import Restaurant
from src.models.user import User
from src.models.produit import Produit
from src.models.ingredient import Ingredient
from src.models.ingredient import Order
from src.models.ingredient import OrderItem
# Cette liste s'allongera à chaque nouveau modèle (Product, Order, OrderItem...)