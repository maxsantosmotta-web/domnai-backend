import pytest

from app.domnai_core.cutover import ControlledCutoverSettings


def test_cutover_accepts_plain_integer(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "1")
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")

    settings = ControlledCutoverSettings.from_env()

    assert settings.traffic_percent == 1


def test_cutover_accepts_equivalent_repeated_assignment(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "1=1")
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")

    settings = ControlledCutoverSettings.from_env()

    assert settings.traffic_percent == 1


def test_cutover_accepts_named_assignment(monkeypatch):
    monkeypatch.setenv(
        "DOMNAI_CUTOVER_TRAFFIC_PERCENT",
        "DOMNAI_CUTOVER_TRAFFIC_PERCENT=1",
    )
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")

    settings = ControlledCutoverSettings.from_env()

    assert settings.traffic_percent == 1


def test_cutover_rejects_ambiguous_assignment(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "2=1")
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")

    with pytest.raises(ValueError, match="atribuição inválida"):
        ControlledCutoverSettings.from_env()


def test_cutover_rejects_non_numeric_value(monkeypatch):
    monkeypatch.setenv("DOMNAI_CUTOVER_TRAFFIC_PERCENT", "um")
    monkeypatch.setenv("DOMNAI_CUTOVER_ENABLED", "false")

    with pytest.raises(ValueError, match="número inteiro"):
        ControlledCutoverSettings.from_env()
