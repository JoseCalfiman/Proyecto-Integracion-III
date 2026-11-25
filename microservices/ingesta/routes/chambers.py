from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import manager, shared
from database import get_db
from models import Chamber
from schemas import ChamberCreate, ChamberRead, ChamberUpdate

router = APIRouter(prefix="/chambers", tags=["chambers"])


def _get_chamber_or_404(db: Session, id_chamber: UUID, user) -> Chamber:
    """Busca una cámara por id; si no existe responde 404."""
    chamber = db.get(Chamber, id_chamber)
    if chamber is None or user.id_company is None or chamber.id_company != user.id_company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    return chamber


# Permisos: técnico y gerente
@router.get("", response_model=List[ChamberRead])
def list_chambers(include_inactive: bool = False, db: Session = Depends(get_db), user=Depends(shared)):
    """Lista las cámaras. Por defecto solo las activas."""
    if user.id_company is None:
        raise HTTPException(403, "Usuario sin empresa")
    query = db.query(Chamber).filter(Chamber.id_company == user.id_company)
    if not include_inactive:
        query = query.filter(Chamber.active.is_(True))
    return query.order_by(Chamber.name).all()


# Permisos: técnico y gerente
@router.get("/{id_chamber}", response_model=ChamberRead)
def get_chamber(id_chamber: UUID, db: Session = Depends(get_db), user=Depends(shared)):
    """Devuelve una cámara por su id."""
    return _get_chamber_or_404(db, id_chamber, user)


# Permisos: solo gerente
@router.post("", response_model=ChamberRead, status_code=status.HTTP_201_CREATED)
def create_chamber(data: ChamberCreate, db: Session = Depends(get_db), user=Depends(manager)):
    """Registra una cámara activa para la empresa del gerente autenticado."""
    if user.id_company is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El gerente no tiene una empresa asociada.")
    if data.id_company is not None and data.id_company != user.id_company:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes registrar cámaras de otra empresa.")
    name = data.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ingresa un nombre válido para la cámara.")
    chamber = Chamber(
        id_company=user.id_company,
        name=name,
        location=(data.location or "").strip() or None,
        active=True,
    )
    try:
        db.add(chamber)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo registrar la cámara por un conflicto de datos.") from exc
    db.refresh(chamber)
    return chamber


# Permisos: solo gerente
@router.put("/{id_chamber}", dependencies=[Depends(manager)], response_model=ChamberRead)
def update_chamber(id_chamber: UUID, data: ChamberUpdate, db: Session = Depends(get_db), user=Depends(manager)):
    """Actualiza solo los campos enviados en el cuerpo de la petición."""
    chamber = _get_chamber_or_404(db, id_chamber, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chamber, field, value)
    db.commit()
    db.refresh(chamber)
    return chamber


# Permisos: solo gerente
@router.delete("/{id_chamber}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chamber(
    id_chamber: UUID, permanent: bool = False,
    db: Session = Depends(get_db), user=Depends(manager),
):
    """Desactiva por defecto; permanent=true elimina el registro y aplica las FK de la BD."""
    chamber = _get_chamber_or_404(db, id_chamber, user)
    if permanent and (user.id_company is None or chamber.id_company != user.id_company):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes eliminar cámaras de otra empresa.")
    try:
        if permanent:
            db.delete(chamber)
        else:
            chamber.active = False
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se pudo eliminar la cámara: existen registros relacionados que impiden la eliminación.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)