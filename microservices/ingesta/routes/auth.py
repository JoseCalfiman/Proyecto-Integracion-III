import os
from time import time

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Role, User
from schemas import LoginRequest

router = APIRouter()


@router.post("/auth/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User.id_user, User.email, User.name, User.password_hash,
                             Role.role_name).join(Role).where(
        User.email == credentials.email.strip(), User.active.is_(True)
    )).one_or_none()
    password = credentials.password.get_secret_value().encode()
    try:
        valid = (user and user.password_hash and len(password) <= 72
                 and bcrypt.checkpw(password, user.password_hash.encode()))
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(503, "Autenticación no configurada")
    token = jwt.encode({"sub": str(user.id_user), "email": user.email,
                        "role": user.role_name, "name": user.name,
                        "exp": int(time()) + 3600}, secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}
