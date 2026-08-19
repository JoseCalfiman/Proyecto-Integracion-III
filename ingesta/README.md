Responsable: Diego Curiqueo

Microservicio que recibe los datos de los sensores (temperatura/consumo), los valida y los guarda en TimescaleDB. Al recibir un dato nuevo, publica un evento nuevos_datos en Redis para que el worker predictivo lo procese.
