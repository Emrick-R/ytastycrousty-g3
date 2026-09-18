# security.py gère les middleware de securité : hashing mdp, verif mdp
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