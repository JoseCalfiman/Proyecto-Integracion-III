import uuid
from sqlalchemy.orm import Session
from models import Prediction

#Guarda la predicción en la tabla 'predictions' del MER oficial, 
#generando o utilizando un UUID y capturando el id_prediction generado.
def persistir_prediccion(db: Session, data_prediccion: dict) -> int:
    # Generar UUID si no viene incluido
    prediction_uuid = data_prediccion.get("uuid", str(uuid.uuid4()))
    
    nueva_prediccion = Prediction(
        uuid=prediction_uuid,
        id_chamber=data_prediccion.get("id_chamber"),
        temperature=data_prediccion.get("temperature"),
        slope_per_minute=data_prediccion.get("slope_per_minute"),
        remaining_time_min=data_prediccion.get("remaining_time_min"),
        risk_level=data_prediccion.get("risk_level"),
        recorded_at=data_prediccion.get("recorded_at")
    )
    
    db.add(nueva_prediccion)
    db.commit()
    db.refresh(nueva_prediccion)  # Refresca para obtener el id_prediction auto-generado
    
    return nueva_prediccion.id_prediction