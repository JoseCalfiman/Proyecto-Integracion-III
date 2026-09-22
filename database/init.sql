-- Esquema base del Proyecto Integracion III (PostgreSQL / TimescaleDB)
-- Tablas usadas por el worker de optimizacion.

-- Precio del kWh (CLP) obtenido desde la API de CNE Chile.
CREATE TABLE IF NOT EXISTS energy_price (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ      NOT NULL,
    price_clp_kwh NUMERIC(12, 4)   NOT NULL,
    source        TEXT             NOT NULL DEFAULT 'cne',
    created_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    UNIQUE (ts, source)
);

CREATE INDEX IF NOT EXISTS idx_energy_price_ts ON energy_price (ts DESC);

-- Consumo electrico diario predicho por Prophet.
CREATE TABLE IF NOT EXISTS predicted_consumption (
    id            BIGSERIAL PRIMARY KEY,
    target_date   DATE             NOT NULL,
    predicted_kwh NUMERIC(12, 4)   NOT NULL,
    yhat_lower    NUMERIC(12, 4),
    yhat_upper    NUMERIC(12, 4),
    model         TEXT             NOT NULL DEFAULT 'prophet',
    created_at    TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_predicted_consumption_date
    ON predicted_consumption (target_date DESC);

-- Recomendaciones de ahorro calculadas por el worker de optimizacion.
CREATE TABLE IF NOT EXISTS saving_recommendation (
    id                 BIGSERIAL PRIMARY KEY,
    target_date        DATE             NOT NULL,
    equipment          TEXT             NOT NULL,
    action             TEXT             NOT NULL,
    time_window        TEXT[],
    hours              NUMERIC(6, 2)    NOT NULL,
    estimated_savings  NUMERIC(12, 2)   NOT NULL,
    price_clp_kwh      NUMERIC(12, 4)   NOT NULL,
    created_at         TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saving_recommendation_date
    ON saving_recommendation (target_date DESC);
