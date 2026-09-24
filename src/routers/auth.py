# Router Auth/Users : login JWT, et CRUD des utilisateurs réservé à l'admin.
# Seul POST /users est imposé par le contrat ; GET/PATCH/DELETE sont un bonus.
import enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.core import verif_hash, creer_jwt, hashing_mdp, require_role, ERR_401, REPONSES_CREATION, ERR_403, \
    REPONSES_LECTURE_PROTEGEE, REPONSES_ECRITURE
from src.models import User

from src.db.database import get_db

router = APIRouter(tags=["Auth & Users"])


# Schéma d'entrée du login : pas de validation des règles ici,
# pour ne rien révéler sur le format attendu des identifiants
class UserLogin(BaseModel):
    username: str
    password: str


# Schéma de sortie du login (format imposé par le contrat)
class TokenOut(BaseModel):
    access_token: str
    token_type: str


# POST /auth/login : renvoie un JWT si les identifiants sont corrects
@router.post("/auth/login", summary="Se connecter et obtenir un token JWT", responses=ERR_401, response_model=TokenOut)
def login(item: UserLogin, db: Session = Depends(get_db)):
    """
        Vérifie l'identifiant et le mot de passe, puis renvoie un **access_token** JWT.

        À coller dans le bouton **Authorize** pour accéder aux routes protégées.
        Identifiants incorrects : **401**, sans préciser lequel est faux. Public.
        """
    user = db.query(User).filter_by(username=item.username).first()
    # 401 générique : on ne dit pas si c'est le user ou le mot de passe qui est faux
    if not user or not verif_hash(item.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants Invalides")
    token = creer_jwt(user.username, user.role)
    return {"access_token": token, "token_type": "bearer"}


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


# POST /users : création d'un utilisateur (admin uniquement)
@router.post("/users", status_code=201, response_model=UserOut, summary="Créer un utilisateur",
             responses=REPONSES_CREATION)
def post_user(item: UserCreate,
              db: Session = Depends(get_db),
              admin: User = Depends(require_role("admin"))  # le fait de déclarer require_role applique le middleware
              ):
    """
        Crée un compte **admin**, **staff** ou **direction**. Réservé à l'**admin**.

        - username : alphanumérique, 8 à 12 caractères, unique
        - mot de passe : 12 à 64 caractères, avec au moins un chiffre, une majuscule et un caractère spécial
        - un **staff** doit être rattaché à un restaurant existant (`restaurant_id`)

        Le mot de passe est stocké hashé et n'apparaît jamais dans la réponse.
        """
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
    db.refresh(nouvel_user)  # on le refresh pour obtenir l'id genere
    return nouvel_user


# --- CRUD complet Users (bonus, au-delà du minimum imposé par le contrat) ---

# GET /users : liste des utilisateurs (admin uniquement, bonus)
@router.get("/users", response_model=list[UserOut], summary="Lister les utilisateurs", responses=ERR_401 | ERR_403)
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    """Liste tous les comptes. Réservé à l'**admin**."""
    """
    Liste tous les comptes. Réservé à l'**admin**.
    """
    return db.query(User).all()


# GET /users/{user_id} : détail d'un utilisateur (admin uniquement, bonus)
@router.get("/users/{user_id}", response_model=UserOut, summary="Consulter un utilisateur",
            responses=REPONSES_LECTURE_PROTEGEE)
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    """Détail d'un compte. Réservé à l'**admin**. **404** si l'utilisateur n'existe pas."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


# PATCH /users/{user_id} : mise à jour partielle (admin uniquement, bonus)
@router.patch("/users/{user_id}", response_model=UserOut, summary="Modifier un utilisateur",
              responses=REPONSES_ECRITURE)
def update_user(user_id: int, item: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    """
    Mise à jour partielle : seuls les champs envoyés sont modifiés. Réservé à l'**admin**.

    Le nouveau mot de passe éventuel suit les mêmes règles qu'à la création.
    Le username n'est pas modifiable.
    """
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
@router.delete("/users/{user_id}", status_code=204, summary="Supprimer un utilisateur", responses=REPONSES_ECRITURE)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    """
    Supprime un compte. Réservé à l'**admin**. Réponse **204** sans contenu.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    db.delete(user)
    db.commit()
