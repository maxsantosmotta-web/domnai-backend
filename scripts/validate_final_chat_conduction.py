from pathlib import Path


PROVIDER_PATH = Path('/app/app/domnai_core/providers.py')


def main() -> None:
    source = PROVIDER_PATH.read_text(encoding='utf-8')

    required = (
        'PROTOCOLO OBRIGATÓRIO DE ENTREGA E ENCERRAMENTO:',
        'resultado completo de uma vez',
        'listas de próximos passos',
        'perguntas genéricas',
        'Encerre naturalmente após a entrega',
        'Agradecimentos, confirmações de entendimento',
        'Correções e complementos do mesmo assunto',
    )
    missing = [text for text in required if text not in source]
    if missing:
        raise RuntimeError(f'Contrato de entrega e encerramento incompleto: {missing}')

    forbidden = (
        'Sempre termine perguntando se o usuário deseja continuar',
        'Sempre ofereça próximos passos',
        'Ofereça várias possibilidades após a resposta',
    )
    present = [text for text in forbidden if text in source]
    if present:
        raise RuntimeError(f'Regras conflitantes de reabertura ainda presentes: {present}')

    compile(source, str(PROVIDER_PATH), 'exec')
    print('Entrega final e encerramento natural validados com sucesso.')


if __name__ == '__main__':
    main()
