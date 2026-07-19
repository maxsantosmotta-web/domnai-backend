from __future__ import annotations

from pathlib import Path


def test_operation_is_initialized_before_existing_result_branch():
    source = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")

    payload_marker = '        payload["task_id"] = task_id\n'
    branch_marker = "    if existing_result is None:\n"
    initialization = '    operation = payload.get("operation")\n'

    payload_index = source.index(payload_marker) + len(payload_marker)
    branch_index = source.index(branch_marker)
    initialization_index = source.index(initialization)

    assert payload_index <= initialization_index < branch_index
