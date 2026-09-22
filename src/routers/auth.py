from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.security import verif_hash, creer_jwt
from src.models.user import User

from src.db.database import get_db

router = APIRouter()

class UserLogin(BaseModel) :
    username: str
    password: str

@router.post("/auth/login")
def login(item: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=item.username).first()
    if not user or not verif_hash(item.password, user.hashed_password) :
        raise HTTPException(status_code=401,detail="Identifiants Invalides")
    token = creer_jwt(user.username, user.role)
    return {"token": token, "token_type": "bearer"}