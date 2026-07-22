from pathlib import Path

path = Path('/app/app/services/chat_task_worker.py')
text = path.read_text(encoding='utf-8')
text = text.replace('usuário):\n"', 'usuário):\\n"')
text = text.replace('+ "\nUse somente fatos', '+ "\\nUse somente fatos')
text = text.replace('USUÁRIO:\n" + "\n\n".join', 'USUÁRIO:\\n" + "\\n\\n".join')
path.write_text(text, encoding='utf-8')
