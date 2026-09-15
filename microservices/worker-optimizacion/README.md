Responsable: Ricardo Aravena

Worker en Celery que, cada cierto número de horas, consulta la API de CNE Chile para obtener el costo del kWh, usa Prophet para predecir el gasto eléctrico del día siguiente y calcula cuánto se ahorraría apagando equipos no críticos en horas de alto costo.



cumple con las tareas pero con datos harcodeados: 

kafka_consumer.py  →  (recibe datos, pero no los pasa a nadie)
scheduler.py       →  (ejecuta build_recommendation, pero con datos fijos)
kafka_producer.py  →  (publica, pero con datos hardcodeados)
optimizer.py       →  (tiene Prophet, pero nadie lo llama)
ahorro.py          →  (tiene el cálculo, pero con precio hardcodeado)

us 5 tareas están cumplidas, pero cada archivo funciona por separado. Falta integrarlos: el consumer debe alimentar al scheduler, el scheduler debe usar Prophet, y el resultado debe guardarse en la BD antes de publicarse en Kafka. Además, el precio no puede estar hardcodeado, debe venir de la tabla energy_price o del archivo precio_cne.csv."

Integrar consumer → scheduler → Prophet → producer	
Usar Prophet real (no datos hardcodeados)	
Guardar en BD (saving_recommendation, predicted_consumption)	
Cambiar localhost:9092 → kafka:9092
Corregir README (quitar Celery)	
Crear Dockerfile	
Leer precio desde BD o archivo (no hardcodeado)

