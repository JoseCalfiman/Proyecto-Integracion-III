import os
import threading
from typing import Callable

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

# Si existe DATABASE_URL se usa tal cual; si no, se arma con las variables PG*
DATABASE_URL = os.getenv("DATABASE_URL") or URL.create(
    "postgresql+psycopg2",
    username=os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
    password=os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    database=os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
)

engine: Engine | None = None
_session_factory: Callable[[], Session] | None = None
_engine_lock = threading.Lock()
Base = declarative_base()


def SessionLocal() -> Session:
    """Crea sesiones a partir de un único engine, inicializado bajo demanda."""
    global engine, _session_factory
    if _session_factory is None:
        with _engine_lock:
            if _session_factory is None:
                engine = create_engine(DATABASE_URL, pool_pre_ping=True)
                _session_factory = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine,
                )
    return _session_factory()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
