--CÁMARAS
INSERT INTO chambers (id_chamber, id_company, name, location, active)
SELECT
  ('aaaaaaaa-aaaa-4aaa-8aaa-' || lpad(n::text, 12, '0'))::uuid,
  '11111111-1111-1111-1111-111111111111',
  'Carga Cámara ' || lpad(n::text, 2, '0'),
  'Prueba de carga',
  TRUE
FROM generate_series(1, 50) AS n
ON CONFLICT (id_chamber) DO NOTHING;

--REGLAS HACCP (una por cámara)
INSERT INTO haccp_rules (id_chamber, tolerance_time_min, max_absolute_temp, min_absolute_temp, severity, active, id_user_modified)
SELECT
  c.id_chamber,
  15,
  CASE WHEN n % 3 = 1 THEN -15 WHEN n % 3 = 2 THEN 4 ELSE 0 END,
  CASE WHEN n % 3 = 1 THEN -30 WHEN n % 3 = 2 THEN 0 ELSE -10 END,
  'medium',
  TRUE,
  '22222222-2222-2222-2222-222222222222'
FROM generate_series(1, 50) AS n
JOIN chambers c
  ON c.id_chamber = ('aaaaaaaa-aaaa-4aaa-8aaa-' || lpad(n::text, 12, '0'))::uuid
WHERE NOT EXISTS (
  SELECT 1 FROM haccp_rules r WHERE r.id_chamber = c.id_chamber
);

--VERIFICACIÓN (debe dar 50 y 50)
SELECT
  (SELECT count(*) FROM chambers WHERE location = 'Prueba de carga') AS camaras_de_carga,
  (SELECT count(*) FROM haccp_rules r JOIN chambers c USING (id_chamber)
    WHERE c.location = 'Prueba de carga')                              AS reglas_de_carga;


--LIMPIEZA (ejecutar SOLO al terminar las pruebas)
--DELETE FROM chambers WHERE location = 'Prueba de carga';