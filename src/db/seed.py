from sqlalchemy.orm import Session

from src.core import hashing_mdp
from src.models import User, Restaurant, Produit


def seed_admin(db: Session):
    adm = db.query(User).filter_by(username="admin123").first()
    if not adm:
        db.add(User(
            first_name="Admin",
            last_name="Ytasty",
            username="admin123",
            hashed_password=hashing_mdp("Admin@123456"),
            role="admin"
        ))
        db.commit()


UTILISATEURS_DEMO = [
    {"first_name": "Sam", "last_name": "Staff", "username": "staffaix1", "password": "Staff@123456", "role": "staff",
     "restaurant_id": 1},
    {"first_name": "Lea", "last_name": "Staff", "username": "stafflyon1", "password": "Staff@123456", "role": "staff",
     "restaurant_id": 2},
    {"first_name": "Dan", "last_name": "Direction", "username": "direction1", "password": "Direction@12345",
     "role": "direction", "restaurant_id": None},
]


def seed_utilisateurs(db: Session):
    for fiche in UTILISATEURS_DEMO:
        existant = db.query(User).filter_by(username=fiche["username"]).first()
        if not existant:
            db.add(User(
                first_name=fiche["first_name"],
                last_name=fiche["last_name"],
                username=fiche["username"],
                # Écriture champ par champ (pas de **) car password devient hashed_password
                hashed_password=hashing_mdp(fiche["password"]),
                role=fiche["role"],
                restaurant_id=fiche["restaurant_id"],
            ))
    db.commit()


RESTAURANT = [
    {
        "name": "Ytasty Crousty Aix",
        "city": "Aix-en-Provence",
        "address": "12 cours Mirabeau",
        "opening_hours": "11h-23h",
        "contact": "0442000001"
    },
    {
        "name": "Ytasty Crousty Lyon",
        "city": "Lyon",
        "address": "5 rue de la République",
        "opening_hours": "11h-23h",
        "contact": "0472000002"
    },
    {
        "name": "Ytasty Crousty Paris",
        "city": "Paris",
        "address": "20 boulevard Saint-Michel",
        "opening_hours": "11h-00h",
        "contact": "0140000003"
    }
]


def seed_restaurant(db: Session):
    for restaurant in RESTAURANT:
        rst = db.query(Restaurant).filter_by(name=restaurant["name"]).first()
        if not rst:
            db.add(Restaurant(**restaurant))
    db.commit()


# restaurant_id : 1 = Aix, 2 = Lyon, 3 = Paris (ordre d'insertion du seed sur une base neuve)
PRODUITS = [
    {"name": "Crispy Chicken Burger", "image": "https://example.com/crispy-chicken.jpg",
     "description": "Burger au poulet pané croustillant", "category": "burgers", "price": 9.9, "is_available": True,
     "restaurant_id": 1, "ingredients": ["pain", "poulet", "salade", "sauce maison"]},
    {"name": "Double Cheese", "image": "https://example.com/double-cheese.jpg",
     "description": "Deux steaks, double cheddar", "category": "burgers", "price": 11.5, "is_available": True,
     "restaurant_id": 1, "ingredients": ["pain", "boeuf", "cheddar", "oignons"]},
    {"name": "Tenders x6", "image": "https://example.com/tenders.jpg", "description": "Six tenders de poulet marinés",
     "category": "chicken", "price": 7.5, "is_available": True, "restaurant_id": 1,
     "ingredients": ["poulet", "chapelure", "épices"]},
    {"name": "Frites maison", "image": "https://example.com/frites.jpg",
     "description": "Frites fraîches coupées sur place", "category": "sides", "price": 3.5, "is_available": False,
     "restaurant_id": 1, "ingredients": ["pommes de terre", "sel"]},
    {"name": "Spicy Chicken Wrap", "image": "https://example.com/spicy-wrap.jpg",
     "description": "Wrap relevé au poulet grillé", "category": "wraps", "price": 8.9, "is_available": True,
     "restaurant_id": 2, "ingredients": ["galette", "poulet", "piment", "cheddar"]},
    {"name": "Veggie Burger", "image": "https://example.com/veggie.jpg", "description": "Galette de légumes et avocat",
     "category": "burgers", "price": 10.5, "is_available": True, "restaurant_id": 2,
     "ingredients": ["pain", "galette de légumes", "avocat", "salade"]},
    {"name": "Milkshake Vanille", "image": "https://example.com/milkshake.jpg",
     "description": "Milkshake onctueux à la vanille", "category": "drinks", "price": 4.5, "is_available": True,
     "restaurant_id": 3, "ingredients": ["lait", "glace vanille"]},
    {"name": "Crousty Box", "image": "https://example.com/crousty-box.jpg",
     "description": "Menu burger, frites et boisson", "category": "menus", "price": 14.9, "is_available": True,
     "restaurant_id": 3, "ingredients": ["burger", "frites", "boisson"]},
    {"name": "Burger Test", "image": "https://example.com/burger.jpg", "description": "Produit créé pour les tests",
     "category": "burgers", "price": 9.9, "is_available": True, "restaurant_id": 1, "ingredients": ["pain", "poulet"]},
]


def seed_produits(db: Session):
    for fiche in PRODUITS:
        # Un même nom de produit peut exister dans deux restaurants : on vérifie le couple nom + restaurant
        existant = db.query(Produit).filter_by(
            name=fiche["name"], restaurant_id=fiche["restaurant_id"]
        ).first()
        if not existant:
            db.add(Produit(**fiche))
    db.commit()
