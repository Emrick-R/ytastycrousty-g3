import enum
from typing import Required

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.core import verif_hash, creer_jwt, hashing_mdp, require_role
from src.models.user import User

from src.db.database import get_db

router = APIRouter()


class UserLogin(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(item: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=item.username).first()
    if not user or not verif_hash(item.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants Invalides")
    token = creer_jwt(user.username, user.role)
    return {"token": token, "token_type": "bearer"}


# Rôles autorisés :
#
# - `admin`
# - `staff`
# - `direction`
class Role(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    direction = "direction"


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str = Field(min_length=8, max_length=12, pattern=r"^[a-zA-Z0-9]+$")
    password: str = Field(min_length=12, max_length=64)
    role: Role
    restaurant_id: int | None = None

    # field_validator permet d'utiliser une fonction méthode dès qu'une instance du modèle est crée avec une valeur dans le champ password
    @field_validator("password")
    @classmethod
    def verifier_password(cls, password: str) -> str:
        if not any(num.isdigit() for num in password):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not any(upp.isupper() for upp in password):  # à toi : condition pour "au moins une majuscule"
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if all(charaNum.isalnum() for charaNum in
               password):  # Pas de fonction spé pour les spéciaux donc on prend ceux qui ne sont pas nombre et lettre
            raise ValueError("Le mot de passe doit contenir au moins un caractère spéciale")
        return password


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: str
    role: Role
    restaurant_id: int | None


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

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    return db.query(User).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


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
        if not any(c.isdigit() for c in password):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not any(c.isupper() for c in password):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if all(c.isalnum() for c in password):
            raise ValueError("Le mot de passe doit contenir au moins un caractère spécial")
        return password


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


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    db.delete(user)
    db.commit()