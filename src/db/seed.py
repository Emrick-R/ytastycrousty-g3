from sqlalchemy.orm import Session

from src.core import hashing_mdp
from src.models import User, Restaurant


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


RESTAURANT = [
    {
        "name": "Ytasty Crousty Aix",
        "city":"Aix-en-Provence",
        "address":"12 cours Mirabeau",
        "opening_hours":"11h-23h",
        "contact":"0442000001"
    },
    {
        "name":"Ytasty Crousty Lyon",
        "city":"Lyon",
        "address":"5 rue de la République",
        "opening_hours":"11h-23h",
        "contact":"0472000002"
    },
    {
        "name":"Ytasty Crousty Paris",
        "city":"Paris",
        "address":"20 boulevard Saint-Michel",
        "opening_hours":"11h-00h",
        "contact":"0140000003"
    }
]

def seed_restaurant(db: Session):
    for restaurant in RESTAURANT :
        rst = db.query(Restaurant).filter_by(name=restaurant["name"]).first()
        if not rst:
            db.add(Restaurant(**restaurant))
    db.commit()