from __future__ import annotations

from pathlib import Path
import re

DISCLAIMER = (
    "Este documento organiza informações para apoio à decisão e não substitui "
    "a avaliação de um profissional habilitado."
)


def _write_compiled(path: Path, source: str) -> None:
    compile(source, str(path), "exec")
    path.write_text(source, encoding="utf-8")


def patch_main() -> None:
    path = Path("/app/app/main.py")
    source = path.read_text(encoding="utf-8")

    source = re.sub(
        r"^from app\.(?:api\.(?:admin_cutover|admin_legacy_retirement|admin_shadow_validation)|domnai_core\.parallel_api_bootstrap|services\.(?:cutover_worker_bootstrap|shadow_validation_worker)) import .*\n",
        "",
        source,
        flags=re.M,
    )
    source = re.sub(
        r"^app\.include_router\((?:admin_cutover_router|admin_legacy_retirement_router|admin_shadow_validation_router)\)\n",
        "",
        source,
        flags=re.M,
    )
    source = re.sub(r"^mount_parallel_api\(app\)\n", "", source, flags=re.M)

    if "from app.services.chat_task_worker import start_chat_task_worker\n" not in source:
        anchor = "from app.frontend_static import FrontendStaticFiles\n"
        if anchor not in source:
            raise RuntimeError("Importação do worker não pôde ser ancorada no app principal.")
        source = source.replace(
            anchor,
            anchor + "from app.services.chat_task_worker import start_chat_task_worker\n",
            1,
        )

    startup_pattern = re.compile(
        r"(@app\.on_event\([\"']startup[\"']\)\n"
        r"def start_persistent_chat_worker\(\):\n)"
        r"(?:[ \t]+.*\n)+",
        flags=re.M,
    )
    source, count = startup_pattern.subn(r"\1    start_chat_task_worker()\n", source, count=1)
    if count != 1 and source.count("start_chat_task_worker()") != 1:
        raise RuntimeError("Inicialização única do worker não localizada.")

    forbidden = (
        "start_cutover_aware_chat_worker(",
        "start_shadow_validation_worker(",
        "mount_parallel_api(",
    )
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f"Referência legada executável permaneceu: {marker}")
    if source.count("start_chat_task_worker()") != 1:
        raise RuntimeError("O worker final precisa iniciar exatamente uma vez.")

    _write_compiled(path, source)


def patch_worker() -> None:
    path = Path("/app/app/services/chat_task_worker.py")
    source = path.read_text(encoding="utf-8")

    source = source.replace(
        "from app.services.orchestrated_brain import generate_orchestrated_response\n",
        "from app.domnai_core.chat_runtime import generate_new_core_response\n",
    )
    source = source.replace(
        "from app.services.diagnosis_memory import load_diagnosis_state, save_diagnosis_state\n",
        "",
    )
    source = re.sub(
        r"\n\s*diagnosis_state = load_diagnosis_state\(user_id, operation\)",
        "",
        source,
        count=1,
    )

    old_call = re.compile(
        r"result = generate_orchestrated_response\(\n"
        r"\s*message=(?:message_for_brain|original_message),\n"
        r"\s*operation=operation,\n"
        r"\s*history=(?:history|contextual_history),\n"
        r"\s*attachments=attachments,\n"
        r"\s*diagnosis_state=diagnosis_state,\n"
        r"\s*\)",
        flags=re.S,
    )
    replacement = """result = generate_new_core_response(
            message=original_message,
            operation=operation,
            history=contextual_history if 'contextual_history' in locals() else history,
            attachments=attachments,
            user_id=user_id,
            task_id=task_id,
        )"""
    source, replaced = old_call.subn(replacement, source, count=1)
    if replaced != 1 and "result = generate_new_core_response(" not in source:
        raise RuntimeError("Chamada do novo núcleo não localizada no worker.")

    source = source.replace(
        "                from app.api.chat import _create_artifact\n                artifact = _create_artifact(",
        "                from app.domnai_core.artifact_delivery import create_artifact\n                artifact = create_artifact(",
    )
    source = source.replace(
        "            from app.api.chat import _artifact_offer\n            offer = _artifact_offer(decision.get(\"artifact_type\"))",
        "            from app.domnai_core.artifact_delivery import artifact_offer\n            offer = artifact_offer(decision.get(\"artifact_type\"))",
    )

    if 'provider="local-artifact"' not in source:
        intelligence = re.compile(
            r"        intelligence_started_at = time\.perf_counter\(\)\n"
            r".*?"
            r"        timings\.update\(getattr\(result, \"timings\", None\) or \{\}\)\n",
            flags=re.S,
        )
        match = intelligence.search(source)
        if not match:
            raise RuntimeError("Bloco de inteligência final não localizado.")
        original = match.group(0)
        nested = "".join("    " + line if line.strip() else line for line in original.splitlines(keepends=True))
        direct = """        pending_artifact = payload.get("pending_artifact")
        pending_source = (
            str(pending_artifact.get("source_answer") or "").strip()
            if isinstance(pending_artifact, dict)
            else ""
        )
        if payload.get("artifact_delivery_state") == "pending" and pending_source:
            from app.services.metered_brain import MeteredBrainResult
            result = MeteredBrainResult(
                text=pending_source,
                provider="local-artifact",
                model="local-artifact",
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                diagnosis_state=None,
            )
            timings["intelligence_ms"] = 0
        else:
""" + nested
        source = source[: match.start()] + direct + source[match.end() :]

    pending_override = """        pending_artifact = payload.get("pending_artifact")
        if payload.get("artifact_delivery_state") == "pending" and isinstance(pending_artifact, dict):
            decision = dict(pending_artifact)
"""
    if pending_override not in source:
        decision_call = re.compile(
            r"(        decision = decide_artifact\(\n.*?        \)\n)",
            flags=re.S,
        )
        source, count = decision_call.subn(lambda m: m.group(1) + pending_override, source, count=1)
        if count != 1:
            raise RuntimeError("Decisão de artefato não localizada.")

    failure_block = re.compile(
        r"            except Exception(?: as \w+)?:\n"
        r"(?:                .*\n)+?"
        r"(?=        elif decision\.get\(\"action\"\) == \"offer\":)",
        flags=re.M,
    )
    canonical_failure = (
        "            except Exception:\n"
        "                print(f\"artifact_delivery failure task_id={task_id}\\n{traceback.format_exc()}\", flush=True)\n"
        "                raise\n"
    )
    source, count = failure_block.subn(lambda _m: canonical_failure, source, count=1)
    if count != 1 and "artifact_delivery failure task_id=" not in source:
        raise RuntimeError("Bloco de falha do artefato não localizado.")

    source = re.sub(
        r"\n\s*if existing_result\.get\(\"diagnosis_state\"\) is not None:.*?\n\s*persistence_started_at =",
        "\n\n    persistence_started_at =",
        source,
        count=1,
        flags=re.S,
    )

    source = source.replace(
        "from app.api.chat import _create_artifact",
        "from app.domnai_core.artifact_delivery import create_artifact",
    )
    source = source.replace("_create_artifact(", "create_artifact(")
    source = source.replace(
        "from app.api.chat import _artifact_offer",
        "from app.domnai_core.artifact_delivery import artifact_offer",
    )
    source = source.replace("_artifact_offer(", "artifact_offer(")

    artifact_timing = '        timings["artifact_ms"] = _elapsed_ms(artifact_started_at)\n'
    if "        artifacts = artifacts[:1]\n" not in source:
        if artifact_timing not in source:
            raise RuntimeError("Fechamento do bloco de artefato não localizado.")
        source = source.replace(
            artifact_timing,
            "        artifacts = artifacts[:1]\n" + artifact_timing,
            1,
        )

    for phrase in (
        "A análise foi concluída, mas não foi possível gerar o arquivo nesta tentativa.",
        "Não foi possível gerar o arquivo nesta tentativa.",
    ):
        source = source.replace(phrase, "")

    forbidden = (
        "generate_orchestrated_response",
        "load_diagnosis_state",
        "save_diagnosis_state",
        "from app.api.chat import _create_artifact",
        "from app.api.chat import _artifact_offer",
    )
    for marker in forbidden:
        if marker in source:
            raise RuntimeError(f"Dependência antiga permaneceu no worker: {marker}")
    if source.count("def _append_completed_response(") != 1:
        raise RuntimeError("A persistência final deve existir exatamente uma vez.")

    _write_compiled(path, source)


def patch_artifact_delivery() -> None:
    path = Path("/app/app/domnai_core/artifact_delivery.py")
    source = path.read_text(encoding="utf-8")
    source = source.replace(
        "            'summary': answer,\n            'sections': [{'title': 'Resultado', 'content': answer}],\n",
        "            'summary': '',\n            'sections': [{'title': 'Conteúdo consolidado', 'content': answer}],\n",
        1,
    )
    if "'summary': answer" in source:
        raise RuntimeError("O conteúdo do PDF continuou duplicado.")
    _write_compiled(path, source)


def patch_pdf_notice() -> None:
    path = Path("/app/app/services/pdf_report.py")
    source = path.read_text(encoding="utf-8")
    old_notice = re.compile(
        r"([\"']Este (?:relatório|documento)[^\"']*(?:habilitado|especializada)\.?[\"'])",
        flags=re.I,
    )
    source = old_notice.sub(repr(DISCLAIMER), source)
    while source.count(DISCLAIMER) > 1:
        index = source.rfind(DISCLAIMER)
        source = source[:index] + source[index + len(DISCLAIMER) :]
    if source.count(DISCLAIMER) != 1:
        raise RuntimeError("O PDF deve conter exatamente um aviso oficial.")
    _write_compiled(path, source)


def validate_runtime() -> None:
    worker = Path("/app/app/services/chat_task_worker.py").read_text(encoding="utf-8")
    main = Path("/app/app/main.py").read_text(encoding="utf-8")
    combined = worker + "\n" + main
    forbidden = (
        "generate_orchestrated_response",
        "diagnosis_memory",
        "load_diagnosis_state",
        "save_diagnosis_state",
        "start_cutover_aware_chat_worker",
        "start_shadow_validation_worker",
        "mount_parallel_api",
        "diagnosis_states",
    )
    for marker in forbidden:
        if marker in combined:
            raise RuntimeError(f"Marcador proibido permaneceu no runtime final: {marker}")


patch_main()
patch_worker()
patch_artifact_delivery()
patch_pdf_notice()
validate_runtime()
print("Runtime canônico de artefatos aplicado e compilado com sucesso.")
