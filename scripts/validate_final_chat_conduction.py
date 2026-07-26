from pathlib import Path


PROVIDER_PATH = Path('/app/app/domnai_core/providers.py')


def main() -> None:
    source = PROVIDER_PATH.read_text(encoding='utf-8')

    required = (
        'PROTOCOLO OBRIGATÓRIO PARA ENTREVISTAS, DIAGNÓSTICOS, PLANOS E RELATÓRIOS:',
        'Antes de responder, identifique todas as informações faltantes que já puder prever',
        'apresente somente as perguntas que ainda faltam',
        'PROTOCOLO OBRIGATÓRIO DE ENTREGA E ENCERRAMENTO:',
        'entregue o resultado completo de uma vez',
        'não apresente listas de próximos passos',
        'Não termine respostas concluídas com perguntas genéricas',
        'Encerre naturalmente após a entrega',
        'Agradecimentos, confirmações de entendimento e encerramentos do usuário',
        'Correções e complementos do mesmo assunto devem ajustar somente o necessário',
    )
    missing = [text for text in required if source.count(text) != 1]
    if missing:
        raise RuntimeError(f'Contrato final de condução incompleto ou duplicado: {missing}')

    forbidden = (
        'Sempre termine perguntando se o usuário deseja continuar',
        'Sempre ofereça próximos passos',
        'Ofereça várias possibilidades após a resposta',
    )
    present = [text for text in forbidden if text in source]
    if present:
        raise RuntimeError(f'Regras conflitantes de reabertura ainda presentes: {present}')

    compile(source, str(PROVIDER_PATH), 'exec')
    print('Coleta, entrega final e encerramento natural validados com sucesso.')


if __name__ == '__main__':
    main()
