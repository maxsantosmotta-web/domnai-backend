import base64

import pytest

from app.domnai_core.attachments import AttachmentPreparer, AttachmentValidationError
from app.domnai_core.contracts import Attachment
from app.domnai_core.tool_execution import ToolExecutionError, ToolExecutor
from app.domnai_core.tools import ToolCall, ToolRegistry


def test_attachment_preparer_builds_image_data_url():
    attachment = Attachment(name="foto.png", mime_type="image/png", content=b"image-bytes")

    prepared = AttachmentPreparer().prepare((attachment,))

    assert prepared[0].content_item["type"] == "input_image"
    assert prepared[0].content_item["image_url"] == (
        "data:image/png;base64," + base64.b64encode(b"image-bytes").decode("ascii")
    )


def test_attachment_preparer_builds_input_file():
    attachment = Attachment(name="documento.pdf", mime_type="application/pdf", content=b"pdf")

    prepared = AttachmentPreparer().prepare((attachment,))

    assert prepared[0].content_item == {
        "type": "input_file",
        "filename": "documento.pdf",
        "file_data": base64.b64encode(b"pdf").decode("ascii"),
    }


def test_attachment_preparer_rejects_empty_file():
    with pytest.raises(AttachmentValidationError, match="está vazio"):
        AttachmentPreparer().prepare(
            (Attachment(name="vazio.txt", mime_type="text/plain", content=b""),)
        )


def test_attachment_preparer_enforces_total_limit():
    preparer = AttachmentPreparer(max_file_bytes=10, max_total_bytes=5)

    with pytest.raises(AttachmentValidationError, match="tamanho total"):
        preparer.prepare(
            (
                Attachment(name="a.txt", mime_type="text/plain", content=b"aaa"),
                Attachment(name="b.txt", mime_type="text/plain", content=b"bbb"),
            )
        )


def test_tool_executor_executes_only_registered_tools():
    registry = ToolRegistry()
    registry.register("somar", lambda args: {"total": args["a"] + args["b"]})

    report = ToolExecutor(registry).execute(
        (ToolCall(name="somar", arguments={"a": 2, "b": 3}),)
    )

    assert report.executed == 1
    assert report.results[0].output == {"total": 5}


def test_tool_executor_enforces_per_turn_limit():
    registry = ToolRegistry()
    registry.register("eco", lambda args: args)
    executor = ToolExecutor(registry, max_calls=1)

    with pytest.raises(ToolExecutionError, match="Limite de 1"):
        executor.execute(
            (
                ToolCall(name="eco", arguments={"value": 1}),
                ToolCall(name="eco", arguments={"value": 2}),
            )
        )


def test_tool_executor_wraps_unregistered_tool_failure():
    with pytest.raises(ToolExecutionError, match="não registrada"):
        ToolExecutor(ToolRegistry()).execute(
            (ToolCall(name="inexistente", arguments={}),)
        )
