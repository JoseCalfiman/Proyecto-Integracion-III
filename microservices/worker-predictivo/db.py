from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from models import Base

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, pool_size=1, max_overflow=0,
    pool_timeout=5,
    connect_args={"connect_timeout": 3, "application_name": "cryometric-predictivo"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def crear_tablas():
    Base.metadata.create_all(bind=engine)
    # create_all no agrega columnas a tablas creadas en versiones anteriores.
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS diagnostico JSON"
        ))