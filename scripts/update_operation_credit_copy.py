from pathlib import Path
import re


ROOT = Path('/frontend/src')
BILLING_PATH = ROOT / 'dashboard-billing-enhancements.js'
APP_PATH = ROOT / 'App.jsx'


NEW_RULES = (
    '<section class="billing-rules-section">'
    '<div class="billing-section-title"><small>Consumo</small><h2>Créditos por operação</h2></div>'
    '<div class="billing-rules-grid">'
    '<span><strong>7 créditos</strong> Diagnóstico, análise ou relatório concluído</span>'
    '<span><strong>Sem nova cobrança</strong> Continuação ou correção do mesmo assunto</span>'
    '<span><strong>Arquivos incluídos</strong> PDF, planilha ou CSV quando disponíveis</span>'
    '</div></section>'
)

OLD_HELP = (
    "    ['Créditos para arquivos', 'Para gerar PDF ou planilha, é necessário possuir no mínimo "
    "7 créditos disponíveis. Se o saldo for insuficiente, o arquivo não será gerado.'],"
)
NEW_HELP = (
    "    ['Créditos por operação', 'Cada operação concluída utiliza 7 créditos. Dependendo do tipo "
    "de análise e do andamento da conversa, o resultado também poderá ser disponibilizado em PDF, "
    "planilha ou CSV. Continuações e correções do mesmo assunto não iniciam uma nova cobrança.'],"
)


def update_billing() -> None:
    source = BILLING_PATH.read_text(encoding='utf-8')
    pattern = re.compile(r'<section class="billing-rules-section">.*?</section>', re.S)
    source, count = pattern.subn(NEW_RULES, source, count=1)
    if count != 1:
        raise RuntimeError('Seção final de consumo não localizada uma única vez.')

    forbidden = (
        'Respostas, conforme o processamento utilizado',
        'PDF gerado pelo chat',
        'Planilha gerada pelo chat',
        'Créditos por utilização',
    )
    remaining = [text for text in forbidden if text in source]
    if remaining:
        raise RuntimeError(f'Nomenclaturas antigas ainda presentes no faturamento: {remaining}')

    for required in (
        'Créditos por operação',
        '7 créditos</strong> Diagnóstico, análise ou relatório concluído',
        'Sem nova cobrança</strong> Continuação ou correção do mesmo assunto',
        'Arquivos incluídos</strong> PDF, planilha ou CSV quando disponíveis',
    ):
        if source.count(required) != 1:
            raise RuntimeError(f'Texto final de faturamento inválido: {required!r}')

    BILLING_PATH.write_text(source, encoding='utf-8')


def update_help() -> None:
    source = APP_PATH.read_text(encoding='utf-8')
    if OLD_HELP in source:
        source = source.replace(OLD_HELP, NEW_HELP, 1)
    elif NEW_HELP not in source:
        marker = "    ['Planos', 'A estrutura de planos será apresentada dentro da plataforma conforme os recursos comerciais forem liberados.'],"
        if marker not in source:
            raise RuntimeError('Seção Planos da Central de Ajuda não localizada.')
        source = source.replace(marker, f'{marker}\n{NEW_HELP}', 1)

    forbidden = (
        "['Créditos para arquivos'",
        'Para gerar PDF ou planilha, é necessário possuir no mínimo 7 créditos disponíveis.',
    )
    remaining = [text for text in forbidden if text in source]
    if remaining:
        raise RuntimeError(f'Nomenclaturas antigas ainda presentes na Central de Ajuda: {remaining}')

    if source.count("['Créditos por operação'") != 1:
        raise RuntimeError('A Central de Ajuda deve conter uma única regra de créditos por operação.')
    if 'Cada operação concluída utiliza 7 créditos.' not in source:
        raise RuntimeError('Explicação oficial de consumo por operação não foi aplicada.')

    APP_PATH.write_text(source, encoding='utf-8')


def main() -> None:
    update_billing()
    update_help()
    print('Nomenclatura final de créditos por operação aplicada e validada com sucesso.')


if __name__ == '__main__':
    main()
