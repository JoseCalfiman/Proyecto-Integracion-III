import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

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

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()