"""Administración de cuentas y empresa, limitada a la empresa del gerente."""
from typing import Literal
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import manager
from database import get_db
from models import Company, Role, User

router = APIRouter(tags=["administración"])


class AccountUpdate(BaseModel):
    rol: Literal["gerente", "tecnico"] | None = None
    activo: bool | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=150)
    password: SecretStr | None = None


class AccountCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=150)
    password: SecretStr
    rol: Literal["gerente", "tecnico"]


def password_hash(password):
    raw = password.get_secret_value().encode()
    if not 1 <= len(raw) <= 72:
        raise HTTPException(422, "La contraseña debe tener entre 1 y 72 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode()


def save_account(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email ya registrado") from None


class CompanyUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)


@router.get("/usuarios")
def list_accounts(actor=Depends(manager), db: Session = Depends(get_db)):
    rows = db.execute(select(User.id_user.label("id"), User.name.label("nombre"), User.email,
                             Role.role_name.label("rol"), User.active.label("activo"))
                      .join(Role).where(User.id_company == actor.id_company))
    return rows.mappings().all()


@router.post("/usuarios", status_code=201)
def create_account(data: AccountCreate, actor=Depends(manager), db: Session = Depends(get_db)):
    account = User(name=data.nombre, email=data.email.strip(), password_hash=password_hash(data.password),
                   id_role=db.execute(select(Role.id_role).where(Role.role_name == data.rol)).scalar_one(),
                   id_company=actor.id_company)
    db.add(account)
    save_account(db)
    return {"id": account.id_user}


@router.put("/usuarios/{user_id}")
def change_access(user_id: UUID, data: AccountUpdate, actor=Depends(manager), db: Session = Depends(get_db)):
    account = db.scalar(select(User).where(User.id_user == user_id, User.id_company == actor.id_company))
    if not account:
        raise HTTPException(404, "Usuario no encontrado")
    if data.rol is not None:
        account.id_role = db.execute(select(Role.id_role).where(Role.role_name == data.rol)).scalar_one()
    if data.activo is not None:
        account.active = data.activo
    if data.nombre is not None:
        account.name = data.nombre
    if data.email is not None:
        account.email = data.email.strip()
    if data.password and data.password.get_secret_value():
        account.password_hash = password_hash(data.password)
    save_account(db)
    return {"id": user_id}


@router.get("/empresa")
def get_company(actor=Depends(manager), db: Session = Depends(get_db)):
    company = db.get(Company, actor.id_company)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")
    return {"id": company.id_company, "nombre": company.name}


@router.put("/empresa")
def update_company(data: CompanyUpdate, actor=Depends(manager), db: Session = Depends(get_db)):
    company = db.get(Company, actor.id_company)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")
    company.name = data.nombre
    db.commit()
    return {"id": company.id_company, "nombre": company.name}
