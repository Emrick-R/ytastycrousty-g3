# Router Auth/Users : login JWT, et CRUD des utilisateurs réservé à l'admin.
# Seul POST /users est imposé par le contrat ; GET/PATCH/DELETE sont un bonus.
import enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.core import verif_hash, creer_jwt, hashing_mdp, require_role
from src.models import User

from src.db.database import get_db

router = APIRouter()

# ---------- Login ----------

# Schéma d'entrée du login : pas de validation des règles ici,
# pour ne rien révéler sur le format attendu des identifiants
class UserLogin(BaseModel):
    username: str
    password: str


# POST /auth/login : renvoie un JWT si les identifiants sont corrects
@router.post("/auth/login")
def login(item: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=item.username).first()
    # 401 générique : on ne dit pas si c'est le user ou le mot de passe qui est faux
    if not user or not verif_hash(item.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants Invalides")
    token = creer_jwt(user.username, user.role)
    return {"access_token": token, "token_type": "bearer"}

# ---------- Schémas Users ----------

# Rôles autorisés par le contrat#
# - `admin`
# - `staff`
# - `direction`
class Role(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    direction = "direction"

# Règles du mot de passe, écrites une seule fois et partagées par UserCreate et UserUpdate
def verifier_regles_mdp(password: str) -> str:
    if not any(c.isdigit() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre")
    if not any(c.isupper() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule")
    # Pas de fonction dédiée aux caractères spéciaux : si tout est lettre ou chiffre, il en manque un
    if all(c.isalnum() for c in password):
        raise ValueError("Le mot de passe doit contenir au moins un caractère spécial")
    return password

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str = Field(min_length=8, max_length=12, pattern=r"^[a-zA-Z0-9]+$")
    password: str = Field(min_length=12, max_length=64)
    role: Role
    restaurant_id: int | None = None

    # field_validator : exécute la fonction à chaque création du modèle avec une valeur pour password
    @field_validator("password")
    @classmethod
    def verifier_password(cls, password: str) -> str:
        return verifier_regles_mdp(password)

# Tous les champs optionnels : seuls ceux envoyés dans le PATCH sont modifiés
class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = Field(default=None, min_length=12, max_length=64)
    role: Role | None = None
    restaurant_id: int | None = None

    @field_validator("password")
    @classmethod
    def verifier_password(cls, password: str | None) -> str | None:
        if password is None:  # champ absent du PATCH -> rien à valider
            return password
        return verifier_regles_mdp(password)

# Schéma de sortie : jamais de mot de passe ni de hash
class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: str
    role: Role
    restaurant_id: int | None


# ---------- Routes Users ----------

# POST /users : création d'un utilisateur (admin uniquement)
@router.post("/users", status_code=201, response_model=UserOut)
def post_user(item: UserCreate,
             db: Session = Depends(get_db),
             admin: User = Depends(require_role("admin"))  # le fait de déclarer require_role applique le middleware
             ):
    user = db.query(User).filter_by(username=item.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Resource déjà existante")
    nouvel_user = User(
        first_name=item.first_name,
        last_name=item.last_name,
        username=item.username,
        hashed_password=hashing_mdp(item.password),
        role=item.role,
        restaurant_id=item.restaurant_id
    )
    db.add(nouvel_user)
    db.commit()
    db.refresh(nouvel_user) # on le refresh pour obtenir l'id genere
    return nouvel_user

# --- CRUD complet Users (bonus, au-delà du minimum imposé par le contrat) ---

# GET /users : liste des utilisateurs (admin uniquement, bonus)
@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    return db.query(User).all()

# GET /users/{user_id} : détail d'un utilisateur (admin uniquement, bonus)
@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


# PATCH /users/{user_id} : mise à jour partielle (admin uniquement, bonus)
@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, item: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if item.first_name is not None:
        user.first_name = item.first_name
    if item.last_name is not None:
        user.last_name = item.last_name
    if item.password is not None:
        user.hashed_password = hashing_mdp(item.password)
    if item.role is not None:
        user.role = item.role
    if item.restaurant_id is not None:
        user.restaurant_id = item.restaurant_id

    db.commit()
    db.refresh(user)
    return user


# DELETE /users/{user_id} : suppression (admin uniquement, bonus), 204 sans contenu
@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    db.delete(user)
    db.commit()