import os
import sys

# Permite `import predictor`, `import contract`, etc. desde tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# kafka_consumer importa db.py, que arma la URL de la base al importarse.
# En tests no se conecta a nada, solo necesita valores válidos.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
