from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from backend.database import config as database_config


def test_initial_migration_creates_current_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    engine = create_engine("sqlite:///:memory:")
    connection = engine.connect()

    alembic_config = Config("alembic.ini")
    alembic_config.attributes["connection"] = connection

    try:
        command.upgrade(alembic_config, "head")
        command.check(alembic_config)
        tables = set(inspect(connection).get_table_names())
    finally:
        connection.close()
        engine.dispose()

    assert {
        "alembic_version",
        "users",
        "transactions",
        "financial_memories",
    } <= tables


def test_init_db_does_not_create_schema_in_production(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(database_config, "engine", engine)
    monkeypatch.setenv("ENVIRONMENT", "production")

    try:
        database_config.init_db()
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()
