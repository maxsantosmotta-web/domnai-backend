from pathlib import Path

path = Path('/frontend/src/App.jsx')
source = path.read_text(encoding='utf-8')

marker = "    ['Planos', 'A estrutura de planos será apresentada dentro da plataforma conforme os recursos comerciais forem liberados.'],"
addition = "    ['Créditos para arquivos', 'Para gerar PDF ou planilha, é necessário possuir no mínimo 7 créditos disponíveis. Se o saldo for insuficiente, o arquivo não será gerado.'],"

if addition not in source:
    if marker not in source:
        raise RuntimeError('Seção Planos da Central de Ajuda não encontrada.')
    source = source.replace(marker, f"{marker}\n{addition}", 1)

path.write_text(source, encoding='utf-8')
