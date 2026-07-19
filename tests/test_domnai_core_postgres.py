from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.domnai_core import (
    ConversationRecord,
    ConversationRequest,
    ConversationResponse,
    PostgresConversationRepository,
    PostgresMemoryStore,
)


def _sqlite_scope_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE domnai_core_memory (
                conversation_id VARCHAR(255) PRIMARY KEY,
                memory_json TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE domnai_core_conversation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id VARCHAR(255) NOT NULL DEFAULT '',
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """))

    @contextmanager
    def scope():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return engine, scope


def test_postgres_memory_store_round_trip_without_touching_legacy_tables():
    _, scope = _sqlite_scope_factory()
    store = PostgresMemoryStore(scope)

    assert store.load("conversation-1") == {}

    store.save("conversation-1", {"project": "DomnAI", "stage": 3})
    assert store.load("conversation-1") == {"project": "DomnAI", "stage": 3}

    store.save("conversation-1", {"project": "DomnAI", "stage": 4})
    assert store.load("conversation-1")["stage"] == 4


def test_postgres_conversation_repository_persists_safe_serialized_record():
    engine, scope = _sqlite_scope_factory()
    repository = PostgresConversationRepository(scope)
    repository.append(
        ConversationRecord(
            conversation_id="conversation-2",
            request=ConversationRequest(message="Analise este arquivo."),
            response=ConversationResponse(
                text="Arquivo analisado.",
                provider="stub",
                model="stub-model",
                input_tokens=10,
                output_tokens=4,
            ),
        )
    )

    with engine.connect() as connection:
        row = connection.execute(text("""
            SELECT conversation_id, request_json, response_json
            FROM domnai_core_conversation_records
        """)).mappings().one()

    assert row["conversation_id"] == "conversation-2"
    assert '"message":"Analise este arquivo."' in row["request_json"]
    assert '"text":"Arquivo analisado."' in row["response_json"]


def test_postgres_memory_rejects_empty_conversation_id_on_save():
    _, scope = _sqlite_scope_factory()
    store = PostgresMemoryStore(scope)

    try:
        store.save("   ", {"invalid": True})
    except ValueError as exc:
        assert "conversation_id" in str(exc)
    else:
        raise AssertionError("Era esperado ValueError para conversation_id vazio.")
