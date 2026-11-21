-- M5. Ejecutar antes de desplegar ingesta sobre una base existente.
-- Las predicciones anteriores conservan diagnostico = NULL.
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS diagnostico JSON;
