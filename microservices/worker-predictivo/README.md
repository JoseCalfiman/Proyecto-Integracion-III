Responsable: Matias Carcamo

Worker en Celery que cada 60 segundos lee el histórico reciente de temperatura desde TimescaleDB, calcula la pendiente con regresión lineal (scikit-learn) y estima el tiempo restante antes de una falla. Si el tiempo restante es ≤ 40 minutos, dispara una alerta.
