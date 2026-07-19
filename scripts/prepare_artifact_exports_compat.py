from pathlib import Path


path = Path("/app/app/services/artifact_decision.py")
text = path.read_text(encoding="utf-8")

expected_threshold = '    return bool(operation and len(str(answer or "").strip()) >= 1000)'
current_decision = '''    explicit_request = _contains_any(normalized, _EXPLICIT_ARTIFACT_MARKERS)
    accepted_previous_offer = offer_already_made and _accepted_offer(normalized)
    return explicit_request or accepted_previous_offer'''
compatible_decision = '''    explicit_request = _contains_any(normalized, _EXPLICIT_ARTIFACT_MARKERS)
    accepted_previous_offer = offer_already_made and _accepted_offer(normalized)
    if explicit_request or accepted_previous_offer:
        return True
    return bool(operation and len(str(answer or "").strip()) >= 1000)'''

if expected_threshold in text:
    print("Compatibilidade de artifact exports já preparada.")
elif current_decision in text:
    path.write_text(text.replace(current_decision, compatible_decision, 1), encoding="utf-8")
    print("Compatibilidade de artifact exports preparada com segurança.")
elif compatible_decision in text:
    print("Compatibilidade de artifact exports já aplicada.")
else:
    raise RuntimeError(
        "artifact exports compatibility: estado inesperado de artifact_decision.py"
    )
