# Centralise l'import de tous les modèles pour que Base les enregistre (nécessaire à la création des tables).
from src.models.restaurant import Restaurant
from src.models.user import User

# Cette liste s'allongera à chaque nouveau modèle (Product, Order, OrderItem...)