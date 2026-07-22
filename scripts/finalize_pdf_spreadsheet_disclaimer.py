from pathlib import Path

DISCLAIMER = (
    'Este documento organiza informações para apoio à decisão e não substitui a avaliação '
    'de profissional habilitado quando o tema exigir análise jurídica, contábil, médica, '
    'financeira ou técnica especializada.'
)

spreadsheet_path = Path('/app/app/services/spreadsheet_artifact.py')
spreadsheet = spreadsheet_path.read_text(encoding='utf-8')

if 'DOCUMENT_DISCLAIMER = (' not in spreadsheet:
    marker = 'from openpyxl.utils import get_column_letter\n\n'
    addition = "DOCUMENT_DISCLAIMER = (\n    'Este documento organiza informações para apoio à decisão e não substitui a avaliação '\n    'de profissional habilitado quando o tema exigir análise jurídica, contábil, médica, '\n    'financeira ou técnica especializada.'\n)\n\n"
    if marker not in spreadsheet:
        raise RuntimeError('Importações da planilha não localizadas.')
    spreadsheet = spreadsheet.replace(marker, marker + addition, 1)

xlsx_marker = '''    for column_index, header in enumerate(clean_headers, start=1):
        max_length = len(header)
        for row_index in range(2, min(len(clean_rows) + 2, 302)):
            value = worksheet.cell(row=row_index, column=column_index).value
            max_length = max(max_length, len(str(value or "")))
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 42)

    output = io.BytesIO()
'''
xlsx_replacement = '''    for column_index, header in enumerate(clean_headers, start=1):
        max_length = len(header)
        for row_index in range(2, min(len(clean_rows) + 2, 302)):
            value = worksheet.cell(row=row_index, column=column_index).value
            max_length = max(max_length, len(str(value or "")))
        worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 42)

    notice = workbook.create_sheet('Aviso')
    notice['A1'] = 'Aviso importante'
    notice['A1'].font = Font(bold=True)
    notice['A2'] = DOCUMENT_DISCLAIMER
    notice['A2'].alignment = Alignment(wrap_text=True, vertical='top')
    notice.column_dimensions['A'].width = 110
    notice.row_dimensions[2].height = 54

    output = io.BytesIO()
'''
if "workbook.create_sheet('Aviso')" not in spreadsheet:
    if xlsx_marker not in spreadsheet:
        raise RuntimeError('Finalização do XLSX não localizada.')
    spreadsheet = spreadsheet.replace(xlsx_marker, xlsx_replacement, 1)

csv_marker = '''    writer.writerow(clean_headers)
    writer.writerows(clean_rows)
    content = text.getvalue().encode("utf-8-sig")
'''
csv_replacement = '''    writer.writerow(clean_headers)
    writer.writerows(clean_rows)
    writer.writerow([])
    writer.writerow(['Aviso importante', DOCUMENT_DISCLAIMER])
    content = text.getvalue().encode("utf-8-sig")
'''
if "writer.writerow(['Aviso importante', DOCUMENT_DISCLAIMER])" not in spreadsheet:
    if csv_marker not in spreadsheet:
        raise RuntimeError('Finalização do CSV não localizada.')
    spreadsheet = spreadsheet.replace(csv_marker, csv_replacement, 1)

spreadsheet_path.write_text(spreadsheet, encoding='utf-8')

pdf_path = Path('/app/app/services/pdf_report.py')
pdf = pdf_path.read_text(encoding='utf-8')
old_pdf_notice = 'Este relatório organiza as informações fornecidas e não substitui avaliação profissional quando o tema exigir análise jurídica, contábil, médica, financeira ou técnica especializada.'
if old_pdf_notice in pdf:
    pdf = pdf.replace(old_pdf_notice, DISCLAIMER, 1)
elif DISCLAIMER not in pdf:
    raise RuntimeError('Aviso final do PDF não localizado.')
pdf_path.write_text(pdf, encoding='utf-8')

for chat_path in (Path('/app/app/api/chat.py'), Path('/app/app/services/chat_task_worker.py')):
    chat = chat_path.read_text(encoding='utf-8')
    old = 'Arquivo criado e enviado aqui no chat.'
    new = 'Arquivo criado e enviado aqui no chat. Este documento não substitui a avaliação de um profissional habilitado quando o tema exigir.'
    if old in chat and new not in chat:
        chat = chat.replace(old, new)
    chat_path.write_text(chat, encoding='utf-8')

print('PDF, XLSX e CSV integrados ao aviso de responsabilidade profissional.')
