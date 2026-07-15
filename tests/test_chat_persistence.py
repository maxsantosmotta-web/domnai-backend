import json
from types import SimpleNamespace

from app.api.chat_state import _merge_server_task_messages


class _Scalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _Db:
    def __init__(self, tasks):
        self._tasks = tasks

    def scalars(self, _query):
        return _Scalars(self._tasks)


def _task(task_id: str, status: str, result: dict | None = None):
    return SimpleNamespace(
        id=task_id,
        user_id="user-1",
        status=status,
        result_json=json.dumps(result, ensure_ascii=False) if result is not None else None,
    )


def test_completed_task_cannot_be_downgraded_by_stale_processing_state():
    task_id = "task-1"
    existing = [{
        "id": f"assistant-{task_id}",
        "role": "assistant",
        "text": "Resposta concluída",
        "attachments": [],
        "sources": [],
        "isError": False,
        "taskId": task_id,
        "processing": False,
    }]
    stale = [{
        "id": f"assistant-{task_id}",
        "role": "assistant",
        "text": "DomnAI está analisando...",
        "attachments": [],
        "sources": [],
        "isError": False,
        "taskId": task_id,
        "processing": True,
    }]
    result = {
        "reply": "Resposta concluída",
        "artifacts": [],
        "sources": [{"title": "Fonte", "url": "https://example.com"}],
    }

    merged = _merge_server_task_messages(
        _Db([_task(task_id, "completed", result)]),
        "user-1",
        stale,
        existing,
    )

    assert merged[0]["text"] == "Resposta concluída"
    assert merged[0]["processing"] is False
    assert merged[0]["isError"] is False
    assert merged[0]["sources"] == result["sources"]


def test_completed_task_cannot_be_replaced_by_connection_error():
    task_id = "task-2"
    completed = [{
        "id": f"assistant-{task_id}",
        "role": "assistant",
        "text": "Resultado final",
        "attachments": [],
        "sources": [],
        "isError": False,
        "taskId": task_id,
        "processing": False,
    }]
    stale_error = [{
        "id": f"assistant-{task_id}",
        "role": "assistant",
        "text": "A conexão com o DomnAI foi interrompida antes da resposta.",
        "attachments": [],
        "sources": [],
        "isError": True,
        "taskId": task_id,
        "processing": False,
    }]

    merged = _merge_server_task_messages(
        _Db([_task(task_id, "completed", {"reply": "Resultado final", "artifacts": [], "sources": []})]),
        "user-1",
        stale_error,
        completed,
    )

    assert merged[0]["text"] == "Resultado final"
    assert merged[0]["isError"] is False


def test_active_task_keeps_server_placeholder_when_client_omits_it():
    task_id = "task-3"
    existing = [
        {
            "id": f"user-{task_id}",
            "role": "user",
            "text": "Analise isto",
            "attachments": [],
            "sources": [],
            "isError": False,
            "taskId": task_id,
            "processing": False,
        },
        {
            "id": f"assistant-{task_id}",
            "role": "assistant",
            "text": "DomnAI está analisando...",
            "attachments": [],
            "sources": [],
            "isError": False,
            "taskId": task_id,
            "processing": True,
        },
    ]

    merged = _merge_server_task_messages(
        _Db([_task(task_id, "processing")]),
        "user-1",
        [],
        existing,
    )

    assert [item["role"] for item in merged] == ["assistant", "user"] or [item["role"] for item in merged] == ["user", "assistant"]
    assert any(item["processing"] for item in merged if item["role"] == "assistant")
