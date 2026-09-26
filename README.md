LÉEME

Ramas: main (estable) → develop (integración) → feature/x-microservicio (trabajo individual)
Flujo: cada persona trabaja en su rama feature/, y hace Pull Request hacia develop cuando su parte funciona.
En los commits pueden usar prefijos como por ejemplo (si lo desean):
feat: agrega endpoint de ingesta
fix: corrige cálculo de pendiente
docs: actualiza README del worker predictivo

Instrucciones de instalación y levantamiento:

    Requisitos previos:
    -Docker Desktop (En Windows, requiere WSL2)
    -Python

    Instalación:
    1-Tener el repositorio para trabajar
    2-Crear tu archivo de variables de entorno (Copia el de .env.example a tu .env y completa los valores en tu .env)
    3-Generar las credenciales de Mosquitto (existe de momento un pwfile en la carpeta mosquitto pero elimina este y crea el tuyo propio con tu valores)
        El broker exige usuario/contraseña (no permite conexiones anónimas) y tiene un control de acceso por tópico (mosquitto/acl.conf) con 3 roles: esp32 (solo publica en sensor/raw), ingesta (solo lee sensor/raw) y admin (acceso total, para pruebas).
        Genera el archivo de contraseñas con mosquitto_passwd (no hace falta tener Mosquitto instalado, se usa la propia imagen de Docker):
            docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd -c /mosquitto/config/pwfile esp32
            docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/pwfile ingesta
            docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/pwfile admin
        Te va a pedir la contraseña de cada usuario por teclado. Usa las mismas contraseñas que pusiste en las variables MQTT_ESP32_PASSWORD, MQTT_INGESTA_PASSWORD y MQTT_ADMIN_PASSWORD de tu .env, para que coincidan. Si tienes problemas de permisos en Windows pon este comando:
            docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 chmod 644 /mosquitto/config/pwfile

    Levantar el proyecto:
    1-docker compose up -d (Los servicios ingesta, worker-predictivo, worker-haccp, worker-optimizacion y dashboard requieren un Dockerfile propio dentro de cada microservices. Si alguno de esos aún no existe, el comando de arriba va a fallar solo para ese servicio. Mientras tanto, puedes levantar únicamente la infraestructura base:
    docker compose up -d mosquitto kafka kafka-init timescaledb)
    2-Verificar está corriendo:
        docker compose ps
    3-Confirmar que los 4 tópicos de Kafka se crearon:
        docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list (Debería mostrar sensor.raw, sensor.anomaly, haccp.alerts, optimization.reports)

    Script de simulación (ESP32 falso):
        Publica datos falsos de temperatura y consumo cada 10 segundos, simulando cámaras reales, para poder probar el sistema sin hardware físico. Corre fuera de Docker, directo en tu pc, por eso usa localhost (variable MQTT_HOST_LOCAL del .env) para conectarse al broker, en vez del nombre mosquitto que usan los servicios que sí corren dentro de la red de Docker.(colocar el siguiente comando si les falta las librerias del script: pip install paho-mqtt python-dotenv)

    Comandos útiles:
        -docker compose up -d (Levanta todos los servicios en segundo plano)
        -docker compose ps (Muestra el estado de los contenedores)
        -docker compose stop (Detiene los contenedores sin borrarlos)
        -docker compose down (Detiene y elimina los contenedores (los datos persisten))
        -docker compose down -v (Detiene, elimina contenedores y borra los datos guardados o volumenes)
