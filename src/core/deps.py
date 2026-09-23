# deps.py : dépendances FastAPI réutilisables sur les routes protégées (auth, vérif rôle...)
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from src.db.database import get_db
from src.models.user import User
from src.core.security import verif_jwt

# # TokenURl renvoi vers la route pour obtenir un token, utile pour l'authorize de Swagger
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

bearer_scheme = HTTPBearer(
    description="Colle ici l'access_token obtenu via POST /auth/login (sans le préfixe 'Bearer' et sans les \" \")"
)

# La route doit être utilise dans un Depends()
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = verif_jwt(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")  # à toi

    username = payload.get("sub")
    user = db.query(User).filter_by(username=username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")  # à toi, même raisonnement que dans login

    return user

# *roles_autorises peut avoir un ou plusieurs arg
def require_role(*roles_autorises: str):
    def verificateur(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles_autorises:
            raise HTTPException(status_code=403, detail="Accès refusé")
        return user
    return verificateur

# Autorisation par restaurant : vérifie qu'un utilisateur a le droit de modifier
# les données (produits, commandes...) d'un restaurant donné. Lève un 403 sinon.
def verifier_acces_restaurant(user: User, restaurant_id: int) -> None:
    # L'admin a accès à tous les restaurants
    if user.role == "admin":
        return
    # Le staff n'a accès qu'à son propre restaurant
    if user.role == "staff" and user.restaurant_id == restaurant_id:
        return
    # Tous les autres cas (direction, staff d'un autre restaurant, rôle inconnu) : refus
    raise HTTPException(status_code=403, detail="Accès refusé à ce restaurant")

# Autorisation en LECTURE sur un restaurant : admin et direction voient tout,
# staff uniquement son restaurant. Lève un 403 sinon.
def verifier_lecture_restaurant(user: User, restaurant_id: int) -> None:
    if user.role in ("admin", "direction"):
        return
    if user.role == "staff" and user.restaurant_id == restaurant_id:
        return
    raise HTTPException(status_code=403, detail="Accès refusé à ce restaurant")