-- ============================================================
-- MER OFICIAL - SMART FRIDGE MONITORING
-- ============================================================

-- 1. Tablas de configuración
CREATE TABLE company (
  id_company UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tax_id VARCHAR(12) NOT NULL UNIQUE,
  name VARCHAR(150),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE roles (
  id_role SERIAL PRIMARY KEY,
  role_name VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE users (
  id_user UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_company UUID REFERENCES company(id_company) ON DELETE CASCADE,
  id_role INT REFERENCES roles(id_role),
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  name VARCHAR(100),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chambers (
  id_chamber UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_company UUID REFERENCES company(id_company) ON DELETE CASCADE,
  name VARCHAR(100),
  location VARCHAR(200),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sensors (
  id_sensor BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  sensor_type VARCHAR(50),
  mqtt_identifier VARCHAR(100),
  model VARCHAR(50),
  mcu_id VARCHAR(50),
  firmware VARCHAR(50),
  last_calibration DATE,
  status VARCHAR(20) DEFAULT 'active',
  installation_date TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Series de tiempo (TimescaleDB)
CREATE TABLE sensor_data (
  id_data BIGSERIAL,
  timestamp TIMESTAMPTZ NOT NULL,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  id_sensor BIGINT REFERENCES sensors(id_sensor) ON DELETE CASCADE,
  insertion_date TIMESTAMPTZ DEFAULT NOW(),
  temperature NUMERIC(5,2),
  consumption_kw NUMERIC(6,3),
  PRIMARY KEY (id_data, timestamp)
);

SELECT create_hypertable('sensor_data', 'timestamp');

-- 3. Reglas HACCP
CREATE TABLE haccp_rules (
  id_rule BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  tolerance_time_min INT,
  active BOOLEAN DEFAULT TRUE,
  review_date TIMESTAMPTZ DEFAULT NOW(),
  max_absolute_temp NUMERIC(5,2),
  min_absolute_temp NUMERIC(5,2),
  severity VARCHAR(20) DEFAULT 'medium'
    CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  id_user_modified UUID REFERENCES users(id_user)
);

-- 4. Predicciones
CREATE TABLE predictions (
  id_prediction BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  calculated_slope NUMERIC(8,4),
  projected_temperature NUMERIC(5,2),
  remaining_time_min NUMERIC(8,2),
  risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  calculation_date TIMESTAMPTZ DEFAULT NOW(),
  id_worker VARCHAR(50)
);

-- 5. Alertas
CREATE TABLE generated_alerts (
  id_alert BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  id_prediction BIGINT REFERENCES predictions(id_prediction) ON DELETE SET NULL,
  id_haccp_rule BIGINT REFERENCES haccp_rules(id_rule) ON DELETE SET NULL,
  alert_type VARCHAR(50),
  severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
  message TEXT,
  generation_date TIMESTAMPTZ DEFAULT NOW(),
  id_user_acknowledged UUID REFERENCES users(id_user),
  acknowledgment_date TIMESTAMPTZ,
  id_user_resolved UUID REFERENCES users(id_user),
  resolution_date TIMESTAMPTZ
);

-- 6. Auditoría de alertas
CREATE TABLE alert_audit (
  id_audit BIGSERIAL PRIMARY KEY,
  id_alert BIGINT REFERENCES generated_alerts(id_alert) ON DELETE CASCADE,
  id_user UUID REFERENCES users(id_user),
  action VARCHAR(50),
  detail TEXT,
  action_date TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Precio de energía
CREATE TABLE energy_price (
  id_price SERIAL PRIMARY KEY,
  price_kwh NUMERIC(10,4) NOT NULL,
  source VARCHAR(100),
  queried_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Consumo predicho
CREATE TABLE predicted_consumption (
  id_consumption_prediction BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  prediction_date DATE,
  predicted_consumption_kw NUMERIC(8,3),
  generation_date TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Recomendaciones de ahorro
CREATE TABLE saving_recommendation (
  id_recommendation BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  id_price INT REFERENCES energy_price(id_price),
  action VARCHAR(100),
  expected_saving_pct NUMERIC(6,3),
  expected_saving_amount NUMERIC(14,4),
  rationale TEXT,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'applied', 'discarded', 'expired')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  applied_at TIMESTAMPTZ
);

-- 10. Preferencias de usuario
CREATE TABLE user_preferences (
  id_preference BIGSERIAL PRIMARY KEY,
  id_user UUID REFERENCES users(id_user) ON DELETE CASCADE UNIQUE,
  idioma VARCHAR(10) DEFAULT 'es-CL',
  zona_horaria VARCHAR(50) DEFAULT 'America/Santiago',
  unidad_temp VARCHAR(10) DEFAULT 'celsius',
  timeout_min INT DEFAULT 30,
  notify_critical BOOLEAN DEFAULT TRUE,
  notify_warning BOOLEAN DEFAULT TRUE,
  notify_info BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Log de ingesta
CREATE TABLE ingestion_log (
  id_log BIGSERIAL PRIMARY KEY,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE CASCADE,
  received_payload TEXT,
  processing_status VARCHAR(20) NOT NULL CHECK (processing_status IN ('success', 'error', 'pending')),
  error_message TEXT,
  reception_date TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Reportes
CREATE TABLE reports (
  id_report BIGSERIAL PRIMARY KEY,
  id_company UUID REFERENCES company(id_company) ON DELETE CASCADE,
  id_user UUID REFERENCES users(id_user),
  report_type VARCHAR(50),
  format VARCHAR(20),
  range_start_date DATE,
  range_end_date DATE,
  file_path VARCHAR(255),
  generation_date TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Conversaciones con IA
CREATE TABLE conversations (
  id_conversation BIGSERIAL PRIMARY KEY,
  id_user UUID REFERENCES users(id_user) ON DELETE CASCADE,
  id_chamber UUID REFERENCES chambers(id_chamber) ON DELETE SET NULL,
  start_date TIMESTAMPTZ DEFAULT NOW(),
  last_activity_date TIMESTAMPTZ DEFAULT NOW(),
  end_date TIMESTAMPTZ
);

CREATE TABLE ai_messages (
  id_message BIGSERIAL PRIMARY KEY,
  id_conversation BIGINT REFERENCES conversations(id_conversation) ON DELETE CASCADE,
  sender VARCHAR(20) NOT NULL CHECK (sender IN ('user', 'assistant')),
  content TEXT,
  sent_date TIMESTAMPTZ DEFAULT NOW()
);

-- 14. Tokens revocados
CREATE TABLE revoked_tokens (
  id_token BIGSERIAL PRIMARY KEY,
  id_user UUID REFERENCES users(id_user) ON DELETE CASCADE,
  token_jti VARCHAR(100) NOT NULL UNIQUE,
  revocation_date TIMESTAMPTZ DEFAULT NOW(),
  original_expiration_date TIMESTAMPTZ
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX idx_sensor_data_chamber ON sensor_data(id_chamber);
CREATE INDEX idx_sensor_data_sensor ON sensor_data(id_sensor);
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp DESC);
CREATE INDEX idx_predictions_chamber ON predictions(id_chamber);
CREATE INDEX idx_alerts_chamber ON generated_alerts(id_chamber);
CREATE INDEX idx_alerts_status ON generated_alerts(status);
CREATE INDEX idx_haccp_rules_chamber ON haccp_rules(id_chamber);
CREATE INDEX idx_ingestion_log_chamber ON ingestion_log(id_chamber);
CREATE INDEX idx_saving_recommendation_chamber ON saving_recommendation(id_chamber);
CREATE INDEX idx_user_preferences_user ON user_preferences(id_user);