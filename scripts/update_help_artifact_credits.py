from pathlib import Path

path = Path('/frontend/src/App.jsx')
source = path.read_text(encoding='utf-8')

marker = "    ['Planos', 'A estrutura de planos será apresentada dentro da plataforma conforme os recursos comerciais forem liberados.'],"
old_addition = "    ['Créditos para arquivos', 'Para gerar PDF ou planilha, é necessário possuir no mínimo 7 créditos disponíveis. Se o saldo for insuficiente, o arquivo não será gerado.'],"
new_addition = "    ['Créditos por operação', 'Cada operação concluída utiliza 7 créditos. Dependendo do tipo de análise e do andamento da conversa, o resultado também poderá ser disponibilizado em PDF, planilha ou CSV. Continuações e correções do mesmo assunto não iniciam uma nova cobrança.'],"

if old_addition in source:
    source = source.replace(old_addition, new_addition, 1)
elif new_addition not in source:
    if marker not in source:
        raise RuntimeError('Seção Planos da Central de Ajuda não encontrada.')
    source = source.replace(marker, f"{marker}\n{new_addition}", 1)

if source.count("['Créditos por operação'") != 1:
    raise RuntimeError('A Central de Ajuda deve conter uma única regra de créditos por operação.')
if "['Créditos para arquivos'" in source:
    raise RuntimeError('A nomenclatura antiga de créditos para arquivos ainda está presente.')

path.write_text(source, encoding='utf-8')
