# security.py gère les middleware de securité : hashing mdp, verif mdp, creation de jwt et décodage
import os
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext

# On prepare le contexte pour le hashing avec bcrypt
mdp_c = CryptContext(schemes=["bcrypt"])


# Permet de hasher le mdp et retourne le mdp hashé
def hashing_mdp(mdp: str) -> str:
    hash_mdp = mdp_c.hash(mdp)
    return hash_mdp

# Vérifie si le mdp est égale au mdp hashé en base.
def verif_hash(mdp: str, mdp_hash: str) -> bool:
    if mdp_c.verify(mdp, mdp_hash):
        return True
    return False

SECRET = os.environ["SECRET_KEY"]
ALGO = "HS256"
PRESCRIPTION = 30 #minutes

def creer_jwt(username: str, role:str):
    return jwt.encode(
        {"sub": username,
         "role": role,
         "exp": datetime.now(timezone.utc) + timedelta(minutes=PRESCRIPTION)
         }, SECRET, algorithm=ALGO)

def verif_jwt(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGO]) # le payload ou erreur