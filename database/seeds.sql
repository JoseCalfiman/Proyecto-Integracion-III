-- ============================================================
-- SEEDS - Datos de ejemplo
-- Smart Fridge Monitoring
-- ============================================================

-- ============================================================
-- 1. EMPRESA
-- ============================================================
INSERT INTO company (id_company, tax_id, name, active)
VALUES
  ('11111111-1111-1111-1111-111111111111', '76.123.456-7', 'Frigorífico del Sur S.A.', TRUE);

-- ============================================================
-- 2. ROLES
-- ============================================================
INSERT INTO roles (id_role, role_name)
VALUES
  (1, 'gerente'),
  (2, 'tecnico');

-- ============================================================
-- 3. USUARIOS
-- Contraseña de ejemplo: "admin123" (hash bcrypt)
-- ============================================================
INSERT INTO users (id_user, id_company, id_role, email, password_hash, name, active)
VALUES
  (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    1,
    'gerente@cryometric.cl',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/if1Hy',
    'Carlos Mendoza',
    TRUE
  ),
  (
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    2,
    'tecnico@cryometric.cl',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/if1Hy',
    'Ana Martínez',
    TRUE
  );

-- ============================================================
-- 4. PREFERENCIAS DE USUARIO
-- ============================================================
INSERT INTO user_preferences (id_user, idioma, zona_horaria, unidad_temp, timeout_min)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'es-CL', 'America/Santiago', 'celsius', 30),
  ('33333333-3333-3333-3333-333333333333', 'es-CL', 'America/Santiago', 'celsius', 30);

-- ============================================================
-- 5. CÁMARAS
-- ============================================================
INSERT INTO chambers (id_chamber, id_company, name, location, active)
VALUES
  (
    '44444444-4444-4444-4444-444444444444',
    '11111111-1111-1111-1111-111111111111',
    'Cámara Principal 01',
    'Sector Norte - Congelados',
    TRUE
  ),
  (
    '55555555-5555-5555-5555-555555555555',
    '11111111-1111-1111-1111-111111111111',
    'Cámara Principal 02',
    'Sector Sur - Refrigerados',
    TRUE
  ),
  (
    '66666666-6666-6666-6666-666666666666',
    '11111111-1111-1111-1111-111111111111',
    'Túnel de Enfriamiento A',
    'Área de Despacho',
    TRUE
  );

-- ============================================================
-- 6. SENSORES
-- ============================================================
INSERT INTO sensors (id_chamber, sensor_type, mqtt_identifier, model, mcu_id, firmware, last_calibration, status)
VALUES
  (
    '44444444-4444-4444-4444-444444444444',
    'temperature',
    'SN-101',
    'PT100',
    'MCU-991',
    'ESP32-S3 v2.1',
    '2026-08-15',
    'active'
  ),
  (
    '44444444-4444-4444-4444-444444444444',
    'humidity',
    'SN-102',
    'DHT22',
    'MCU-991',
    'ESP32-S3 v2.1',
    '2026-08-15',
    'active'
  ),
  (
    '55555555-5555-5555-5555-555555555555',
    'temperature',
    'SN-103',
    'PT100',
    'MCU-992',
    'ESP32-S3 v2.1',
    '2026-07-20',
    'active'
  ),
  (
    '66666666-6666-6666-6666-666666666666',
    'temperature',
    'SN-104',
    'PT100',
    'MCU-993',
    'ESP32-S3 v2.1',
    '2026-09-01',
    'maintenance'
  );

-- ============================================================
-- 7. REGLAS HACCP
-- ============================================================
INSERT INTO haccp_rules (id_chamber, tolerance_time_min, max_absolute_temp, min_absolute_temp, severity, active, id_user_modified)
VALUES
  (
    '44444444-4444-4444-4444-444444444444',
    15,
    -18.0,
    -25.0,
    'critical',
    TRUE,
    '22222222-2222-2222-2222-222222222222'
  ),
  (
    '55555555-5555-5555-5555-555555555555',
    30,
    4.0,
    -4.0,
    'medium',
    TRUE,
    '22222222-2222-2222-2222-222222222222'
  ),
  (
    '66666666-6666-6666-6666-666666666666',
    20,
    2.0,
    -10.0,
    'high',
    TRUE,
    '22222222-2222-2222-2222-222222222222'
  );

-- ============================================================
-- 8. PRECIO DE ENERGÍA (CNE)
-- ============================================================
INSERT INTO energy_price (price_kwh, source)
VALUES
  (145.5000, 'CNE - Informe Octubre 2026'),
  (148.2000, 'CNE - Informe Noviembre 2026');

-- ============================================================
-- 9. PREDICCIONES DE EJEMPLO
-- ============================================================
INSERT INTO predictions (id_chamber, calculated_slope, projected_temperature, remaining_time_min, risk_level, id_worker)
VALUES
  ('44444444-4444-4444-4444-444444444444', 0.4000, -18.2, 145.00, 'low', 'worker-predictivo-1'),
  ('55555555-5555-5555-5555-555555555555', 1.8000, -12.5, 42.00, 'medium', 'worker-predictivo-1'),
  ('66666666-6666-6666-6666-666666666666', 4.2000, -4.8, 12.00, 'critical', 'worker-predictivo-1'),
  ('44444444-4444-4444-4444-444444444444', 0.2000, -19.1, 180.00, 'low', 'worker-predictivo-1');

-- ============================================================
-- 10. ALERTAS GENERADAS
-- ============================================================
INSERT INTO generated_alerts (id_chamber, id_prediction, id_haccp_rule, alert_type, severity, status, message)
VALUES
  (
    '66666666-6666-6666-6666-666666666666',
    3,
    3,
    'haccp_violation',
    'critical',
    'active',
    'Temperatura excedió límite superior (-18°C) por más de 15 min. Actual: -15.3°C'
  ),
  (
    '55555555-5555-5555-5555-555555555555',
    2,
    2,
    'threshold_nearing',
    'medium',
    'acknowledged',
    'Fluctuación anómala detectada en ciclo de deshielo. Actual: 3.1°C'
  );

-- ============================================================
-- 11. RECOMENDACIONES DE AHORRO
-- ============================================================
INSERT INTO saving_recommendation (id_chamber, id_price, action, expected_saving_pct, expected_saving_amount, rationale, status)
VALUES
  (
    '44444444-4444-4444-4444-444444444444',
    1,
    'Ajuste de Setpoint Cámara 3',
    15.000,
    45000.0000,
    'Elevar el setpoint en horario valle (02:00 - 06:00) mantendrá la cadena de frío (-18°C) reduciendo ciclos del compresor.',
    'pending'
  ),
  (
    '55555555-5555-5555-5555-555555555555',
    1,
    'Optimización Defrost Cámara 1',
    8.000,
    28000.0000,
    'Retrasar el ciclo de deshielo programado 45 minutos para evitar solapamiento con pico tarifario.',
    'pending'
  ),
  (
    '66666666-6666-6666-6666-666666666666',
    2,
    'Secuenciación de Compresores',
    12.000,
    77000.0000,
    'Implementar arranque escalonado en Planta Central para reducir penalizaciones por demanda máxima de kW.',
    'applied'
  );

-- ============================================================
-- FIN DE LOS SEEDS
-- ============================================================