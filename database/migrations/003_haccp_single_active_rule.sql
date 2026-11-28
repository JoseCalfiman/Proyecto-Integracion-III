-- A6. Una sola regla HACCP activa por cámara.
-- Ejecutar una vez sobre una base existente antes (o justo después) de desplegar
-- la versión de ingesta que muestra la regla vigente en "Reglas HACCP". Así el
-- worker-haccp, que usa la regla activa más reciente, aplica la misma regla que
-- la UI muestra (la más reciente: review_date DESC, id_rule DESC).
-- Bases nuevas no la necesitan. Es idempotente y no borra filas: solo pone
-- active = false en las reglas que no son la vigente de su cámara.
WITH ranked AS (
  SELECT id_rule,
         ROW_NUMBER() OVER (
           PARTITION BY id_chamber
           ORDER BY review_date DESC, id_rule DESC
         ) AS position
  FROM haccp_rules
)
UPDATE haccp_rules AS rule
SET active = FALSE
FROM ranked
WHERE rule.id_rule = ranked.id_rule
  AND ranked.position > 1
  AND rule.active IS DISTINCT FROM FALSE;
