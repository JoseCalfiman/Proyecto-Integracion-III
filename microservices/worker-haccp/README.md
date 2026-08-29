Responsable: Eduardo Dominguez

Microservicio que escucha los eventos de riesgo (alerta_tecnica) publicados en Redis, aplica las reglas HACCP definidas (por ejemplo, temperatura > 4°C por más de 2 minutos) y envía la notificación correspondiente al bot de Telegram. Además, guarda un log de cada alerta en la base de datos.
