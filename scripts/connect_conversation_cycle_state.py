from __future__ import annotations

from pathlib import Path


WORKER_PATH = Path('/app/app/services/chat_task_worker.py')


def _assert_cycle_logic() -> None:
    from app.services.conversation_cycle import build_cycle_state, latest_cycle_state

    first = build_cycle_state(operation='Análise imobiliária', message='Quero avaliar um imóvel.', previous=None)
    continued = build_cycle_state(operation='Análise imobiliária', message='O imóvel tem 120 m².', previous=first)
    changed = build_cycle_state(operation='Exercício em casa', message='Monte um treino.', previous=continued)

    assert first['cycleId'] == continued['cycleId'], 'A mesma operação deve preservar o ciclo.'
    assert first['firstMessage'] == continued['firstMessage'], 'A primeira mensagem deve ser preservada.'
    assert changed['cycleId'] != continued['cycleId'], 'A troca objetiva de operação deve abrir novo ciclo.'
    assert latest_cycle_state([{'role': 'assistant', 'contextState': continued}])['cycleId'] == continued['cycleId']
    assert latest_cycle_state([{'role': 'assistant'}]) is None


def main() -> None:
    source = WORKER_PATH.read_text(encoding='utf-8')

    import_anchor = 'from app.services.credit_meter import charge_usage, ensure_minimum_credit\n'
    import_line = 'from app.services.conversation_cycle import build_cycle_state, latest_cycle_state\n'
    if import_line not in source:
        if import_anchor not in source:
            raise RuntimeError('Importação de credit_meter não localizada no worker final.')
        source = source.replace(import_anchor, import_anchor + import_line, 1)

    messages_anchor = '''        except json.JSONDecodeError:
            messages = []

        replaced = False
'''
    messages_replacement = '''        except json.JSONDecodeError:
            messages = []

        previous_context_state = latest_cycle_state(messages)
        context_state = build_cycle_state(
            operation=payload.get("operation"),
            message=str(payload.get("message") or ""),
            previous=previous_context_state,
        )

        replaced = False
'''
    if messages_replacement not in source:
        if messages_anchor not in source:
            raise RuntimeError('Ponto de criação do estado da conversa não localizado no worker final.')
        source = source.replace(messages_anchor, messages_replacement, 1)

    replacement_anchor = '''                "processing": False,
                "taskId": task_id,
            }
'''
    replacement_value = '''                "processing": False,
                "taskId": task_id,
                "contextState": context_state,
            }
'''
    if replacement_value not in source:
        if replacement_anchor not in source:
            raise RuntimeError('Mensagem substituída do assistente não localizada no worker final.')
        source = source.replace(replacement_anchor, replacement_value, 1)

    append_anchor = '''                "taskId": task_id,
                "processing": False,
            })

        state.messages_json'''
    append_value = '''                "taskId": task_id,
                "processing": False,
                "contextState": context_state,
            })

        state.messages_json'''
    if append_value not in source:
        if append_anchor not in source:
            raise RuntimeError('Mensagem anexada do assistente não localizada no worker final.')
        source = source.replace(append_anchor, append_value, 1)

    compile(source, str(WORKER_PATH), 'exec')
    WORKER_PATH.write_text(source, encoding='utf-8')

    final_source = WORKER_PATH.read_text(encoding='utf-8')
    assert final_source.count('contextState": context_state') == 2
    assert final_source.count('build_cycle_state(') == 1
    assert final_source.count('latest_cycle_state(') == 1
    _assert_cycle_logic()
    print('Estado estruturado do ciclo conectado e testado com sucesso.')


if __name__ == '__main__':
    main()
