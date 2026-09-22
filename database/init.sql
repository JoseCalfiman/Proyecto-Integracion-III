-- =====================================================================
-- Cold-Chain / HACCP Monitoring System — PostgreSQL Schema
-- Translated from Spanish ER diagram (MER) to English + PostgreSQL DDL
-- =====================================================================
-- Notes on translation choices:
--   camaras            -> chambers        (cold storage / refrigeration chambers)
--   empresas           -> companies
--   usuarios           -> users
--   sensores           -> sensors
--   alertas_generadas  -> generated_alerts
--   predicciones_generadas -> generated_predictions
--   consumo_predicho   -> predicted_consumption
--   reglas_haccp       -> haccp_rules
--   log_ingesta        -> ingestion_log
--   auditoria_alertas  -> alert_audit_log
--   conversaciones_ia  -> ai_conversations
--   mensajes_ia        -> ai_messages
--   precio_energia     -> energy_price
--   saving_recommendation -> saving_recommendations
--   tokens_revocados   -> revoked_tokens
--   "timestamp" is a reserved word in SQL, renamed to recorded_at
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- roles
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    role_id     SERIAL PRIMARY KEY,
    role_name   VARCHAR(50) NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- companies (empresas)
-- ---------------------------------------------------------------------
CREATE TABLE companies (
    company_id  SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    tax_id      VARCHAR(20)  NOT NULL UNIQUE,   -- RUT
    address     VARCHAR(200),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- users (usuarios)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    company_id      INT NOT NULL REFERENCES companies(company_id),
    role_id         INT NOT NULL REFERENCES roles(role_id),
    name            VARCHAR(150) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMP
);

-- ---------------------------------------------------------------------
-- chambers (camaras)
-- ---------------------------------------------------------------------
CREATE TABLE chambers (
    chamber_id          SERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(company_id),
    name                VARCHAR(150) NOT NULL,
    location            VARCHAR(200),
    operating_max_temp  NUMERIC(6,2),
    operating_min_temp  NUMERIC(6,2),
    status              VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- sensors (sensores)
-- ---------------------------------------------------------------------
CREATE TABLE sensors (
    sensor_id           SERIAL PRIMARY KEY,
    chamber_id          INT NOT NULL REFERENCES chambers(chamber_id),
    sensor_type         VARCHAR(50) NOT NULL,
    mqtt_identifier      VARCHAR(150) NOT NULL UNIQUE,
    model               VARCHAR(100),
    status              VARCHAR(30) NOT NULL DEFAULT 'active',
    installation_date   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- sensor_data (time-series readings)
-- ---------------------------------------------------------------------
CREATE TABLE sensor_data (
    data_id         BIGSERIAL,
    recorded_at     TIMESTAMP NOT NULL,
    chamber_id      INT NOT NULL REFERENCES chambers(chamber_id),
    sensor_id       INT NOT NULL REFERENCES sensors(sensor_id),
    temperature     NUMERIC(6,2),
    consumption_kw  NUMERIC(10,3),
    inserted_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (data_id, recorded_at)
);
CREATE INDEX idx_sensor_data_chamber ON sensor_data(chamber_id);
CREATE INDEX idx_sensor_data_sensor  ON sensor_data(sensor_id);

-- ---------------------------------------------------------------------
-- haccp_rules (reglas_haccp)
-- ---------------------------------------------------------------------
CREATE TABLE haccp_rules (
    rule_id                 SERIAL PRIMARY KEY,
    chamber_id              INT NOT NULL REFERENCES chambers(chamber_id),
    absolute_max_temp       NUMERIC(6,2) NOT NULL,
    absolute_min_temp       NUMERIC(6,2) NOT NULL,
    tolerance_time_min      INT NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP,
    modified_by_user_id     INT REFERENCES users(user_id)
);

-- ---------------------------------------------------------------------
-- generated_predictions (predicciones_generadas)
-- ---------------------------------------------------------------------
CREATE TABLE generated_predictions (
    prediction_id           BIGSERIAL PRIMARY KEY,
    chamber_id              INT NOT NULL REFERENCES chambers(chamber_id),
    calculated_slope        NUMERIC(10,4),
    projected_temperature   NUMERIC(6,2),
    remaining_time_min      NUMERIC(10,2),
    risk_level              VARCHAR(30),
    calculated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- generated_alerts (alertas_generadas)
-- ---------------------------------------------------------------------
CREATE TABLE generated_alerts (
    alert_id                BIGSERIAL PRIMARY KEY,
    chamber_id              INT NOT NULL REFERENCES chambers(chamber_id),
    prediction_id           BIGINT REFERENCES generated_predictions(prediction_id),
    haccp_rule_id           INT REFERENCES haccp_rules(rule_id),
    alert_type              VARCHAR(50) NOT NULL,
    severity                VARCHAR(30) NOT NULL,
    status                  VARCHAR(30) NOT NULL DEFAULT 'open',
    message                 VARCHAR(500),
    generated_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    acknowledged_by_user_id INT REFERENCES users(user_id),
    acknowledged_at         TIMESTAMP,
    resolved_by_user_id     INT REFERENCES users(user_id),
    resolved_at             TIMESTAMP
);

-- ---------------------------------------------------------------------
-- alert_audit_log (auditoria_alertas)
-- ---------------------------------------------------------------------
CREATE TABLE alert_audit_log (
    audit_id    BIGSERIAL PRIMARY KEY,
    alert_id    BIGINT NOT NULL REFERENCES generated_alerts(alert_id),
    user_id     INT NOT NULL REFERENCES users(user_id),
    action      VARCHAR(50) NOT NULL,
    detail      VARCHAR(500),
    action_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- predicted_consumption (consumo_predicho)
-- ---------------------------------------------------------------------
CREATE TABLE predicted_consumption (
    consumption_prediction_id  BIGSERIAL PRIMARY KEY,
    chamber_id                 INT NOT NULL REFERENCES chambers(chamber_id),
    prediction_date             DATE NOT NULL,
    predicted_consumption_kw   NUMERIC(10,3),
    generated_at                TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- energy_price (precio_energia)
-- ---------------------------------------------------------------------
CREATE TABLE energy_price (
    price_id     SERIAL PRIMARY KEY,
    price_kwh    NUMERIC(10,4) NOT NULL,
    source       VARCHAR(100),
    queried_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- saving_recommendations (saving_recommendation)
-- ---------------------------------------------------------------------
CREATE TABLE saving_recommendations (
    recommendation_id  BIGSERIAL PRIMARY KEY,
    company_id          INT NOT NULL REFERENCES companies(company_id),
    chamber_id          INT NOT NULL REFERENCES chambers(chamber_id),
    price_id             INT REFERENCES energy_price(price_id),
    action               VARCHAR(150) NOT NULL,
    savings_percentage  NUMERIC(5,2),
    amount_clp          NUMERIC(12,2),
    justification        TEXT,
    status               VARCHAR(30) NOT NULL DEFAULT 'pending',
    generated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- reports (reportes)
-- ---------------------------------------------------------------------
CREATE TABLE reports (
    report_id           SERIAL PRIMARY KEY,
    company_id           INT NOT NULL REFERENCES companies(company_id),
    user_id               INT NOT NULL REFERENCES users(user_id),
    report_type           VARCHAR(50) NOT NULL,
    format                VARCHAR(20) NOT NULL,
    range_start_date      DATE,
    range_end_date         DATE,
    file_path              VARCHAR(300),
    generated_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- ai_conversations (conversaciones_ia)
-- ---------------------------------------------------------------------
CREATE TABLE ai_conversations (
    conversation_id       SERIAL PRIMARY KEY,
    user_id                INT NOT NULL REFERENCES users(user_id),
    chamber_id             INT REFERENCES chambers(chamber_id),
    started_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity_at        TIMESTAMP
);

-- ---------------------------------------------------------------------
-- ai_messages (mensajes_ia)
-- ---------------------------------------------------------------------
CREATE TABLE ai_messages (
    message_id       BIGSERIAL PRIMARY KEY,
    conversation_id   INT NOT NULL REFERENCES ai_conversations(conversation_id),
    sender             VARCHAR(20) NOT NULL,   -- e.g. 'user' / 'assistant'
    content             TEXT NOT NULL,
    sent_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- revoked_tokens (tokens_revocados)
-- ---------------------------------------------------------------------
CREATE TABLE revoked_tokens (
    token_id                    SERIAL PRIMARY KEY,
    user_id                       INT NOT NULL REFERENCES users(user_id),
    token_jti                     VARCHAR(255) NOT NULL UNIQUE,
    revocation_date                TIMESTAMP NOT NULL DEFAULT NOW(),
    original_expiration_date       TIMESTAMP
);

-- ---------------------------------------------------------------------
-- ingestion_log (log_ingesta)
-- ---------------------------------------------------------------------
CREATE TABLE ingestion_log (
    log_id                 BIGSERIAL PRIMARY KEY,
    chamber_id              INT NOT NULL REFERENCES chambers(chamber_id),
    received_payload         TEXT,
    processing_status        VARCHAR(30) NOT NULL,
    error_message             VARCHAR(500),
    received_at                TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- Helpful indexes on foreign keys not already covered above
-- ---------------------------------------------------------------------
CREATE INDEX idx_users_company            ON users(company_id);
CREATE INDEX idx_users_role                ON users(role_id);
CREATE INDEX idx_chambers_company          ON chambers(company_id);
CREATE INDEX idx_sensors_chamber           ON sensors(chamber_id);
CREATE INDEX idx_haccp_rules_chamber       ON haccp_rules(chamber_id);
CREATE INDEX idx_generated_predictions_chamber ON generated_predictions(chamber_id);
CREATE INDEX idx_generated_alerts_chamber  ON generated_alerts(chamber_id);
CREATE INDEX idx_generated_alerts_prediction ON generated_alerts(prediction_id);
CREATE INDEX idx_alert_audit_log_alert     ON alert_audit_log(alert_id);
CREATE INDEX idx_predicted_consumption_chamber ON predicted_consumption(chamber_id);
CREATE INDEX idx_saving_recommendations_company ON saving_recommendations(company_id);
CREATE INDEX idx_saving_recommendations_chamber ON saving_recommendations(chamber_id);
CREATE INDEX idx_reports_company           ON reports(company_id);
CREATE INDEX idx_ai_conversations_user     ON ai_conversations(user_id);
CREATE INDEX idx_ai_messages_conversation  ON ai_messages(conversation_id);
CREATE INDEX idx_revoked_tokens_user       ON revoked_tokens(user_id);
CREATE INDEX idx_ingestion_log_chamber     ON ingestion_log(chamber_id);

COMMIT;
