"""Autenticación Bearer y autorización usando el rol vigente de la cuenta."""
import os
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Role, User

bearer = HTTPBearer(auto_error=False)


def signing_key():
    key = os.getenv("JWT_SECRET", "")
    if len(key.encode()) < 32:
        raise HTTPException(503, "Autenticación no configurada")
    return key


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                     db: Session = Depends(get_db)):
    unauthorized = HTTPException(401, "Token inválido o vencido", headers={"WWW-Authenticate": "Bearer"})
    if not credentials:
        raise unauthorized
    try:
        claims = jwt.decode(credentials.credentials, signing_key(), algorithms=["HS256"],
                            options={"require": ["sub", "role", "exp"]})
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, TypeError, ValueError, AttributeError):
        raise unauthorized from None
    user = db.execute(select(User.id_user, User.id_company, Role.role_name).join(Role)
                      .where(User.id_user == user_id, User.active.is_(True))).one_or_none()
    if not user or user.role_name != claims["role"]:
        raise unauthorized
    return user


def require_role(*roles):
    def check(user=Depends(get_current_user)):
        if user.role_name not in roles:
            raise HTTPException(403, "Rol sin permiso para esta operación")
        return user
    return check


shared = require_role("gerente", "tecnico")
manager = require_role("gerente")
technician = require_role("tecnico")
