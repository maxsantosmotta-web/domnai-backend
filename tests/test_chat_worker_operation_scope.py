from pathlib import Path


def test_operation_is_initialized_before_existing_result_branch():
    source = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")

    assignment = '        operation = payload.get("operation")'
    conditional = "    if existing_result is None:"

    assert source.count(assignment) == 1
    assert assignment in source
    assert conditional in source
    assert source.index(assignment) < source.index(conditional)


def test_worker_logs_full_traceback_on_task_failure():
    source = Path("app/services/chat_task_worker.py").read_text(encoding="utf-8")

    assert "import traceback" in source
    assert "traceback.format_exc()" in source
    assert "task_id={task_id}" in source
