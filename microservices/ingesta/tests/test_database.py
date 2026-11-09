from unittest.mock import Mock

import database


def test_session_factory_is_created_once_and_reused(monkeypatch):
    engine = object()
    sessions = [object(), object()]
    factory = Mock(side_effect=sessions)
    create_engine = Mock(return_value=engine)
    sessionmaker = Mock(return_value=factory)

    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "_session_factory", None)
    monkeypatch.setattr(database, "create_engine", create_engine)
    monkeypatch.setattr(database, "sessionmaker", sessionmaker)

    assert database.SessionLocal() is sessions[0]
    assert database.SessionLocal() is sessions[1]

    create_engine.assert_called_once_with(database.DATABASE_URL, pool_pre_ping=True)
    sessionmaker.assert_called_once_with(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
