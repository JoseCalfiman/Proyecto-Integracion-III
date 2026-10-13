from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from models import Chamber
from schemas import ChamberCreate, ChamberRead, ChamberUpdate

router = APIRouter(prefix="/chambers", tags=["chambers"])


def _get_chamber_or_404(db: Session, id_chamber: UUID) -> Chamber:
    """Busca una cámara por id; si no existe responde 404."""
    chamber = db.get(Chamber, id_chamber)
    if chamber is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    return chamber


# Permisos: técnico y gerente (TODO: agregar dependencia de auth cuando exista auth.py)
@router.get("", response_model=List[ChamberRead])
def list_chambers(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Lista las cámaras. Por defecto solo las activas."""
    query = db.query(Chamber)
    if not include_inactive:
        query = query.filter(Chamber.active.is_(True))
    return query.order_by(Chamber.name).all()


# Permisos: técnico y gerente
@router.get("/{id_chamber}", response_model=ChamberRead)
def get_chamber(id_chamber: UUID, db: Session = Depends(get_db)):
    """Devuelve una cámara por su id."""
    return _get_chamber_or_404(db, id_chamber)


# Permisos: solo gerente
@router.post("", response_model=ChamberRead, status_code=status.HTTP_201_CREATED)
def create_chamber(data: ChamberCreate, db: Session = Depends(get_db)):
    """Crea una cámara nueva."""
    chamber = Chamber(**data.model_dump())
    db.add(chamber)
    db.commit()
    db.refresh(chamber)
    return chamber


# Permisos: solo gerente
@router.put("/{id_chamber}", response_model=ChamberRead)
def update_chamber(id_chamber: UUID, data: ChamberUpdate, db: Session = Depends(get_db)):
    """Actualiza solo los campos enviados en el cuerpo de la petición."""
    chamber = _get_chamber_or_404(db, id_chamber)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chamber, field, value)
    db.commit()
    db.refresh(chamber)
    return chamber


# Permisos: solo gerente
@router.delete("/{id_chamber}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chamber(id_chamber: UUID, db: Session = Depends(get_db)):
    """Desactiva la cámara (borrado lógico), no elimina el registro."""
    chamber = _get_chamber_or_404(db, id_chamber)
    chamber.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)