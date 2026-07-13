from pathlib import Path
import re

path = Path('/frontend/src/dashboard-billing-enhancements.js')
source = path.read_text(encoding='utf-8')

source, count = re.subn(
    r"\nfunction transactionLabel\(item\) \{.*?\n\}\n",
    "\n",
    source,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('Não foi possível remover o rótulo interno de movimentações.')

source = source.replace(
    "function renderBilling(section, status, transactions, selectedPeriod = 'monthly') {",
    "function renderBilling(section, status, selectedPeriod = 'monthly') {",
    1,
)

history_pattern = re.compile(
    r"\n\s*<section class=\"billing-history-section\">.*?</section>",
    re.S,
)
source, count = history_pattern.subn("", source, count=1)
if count != 1:
    raise RuntimeError('Não foi possível remover o histórico visual do faturamento.')

source = source.replace(
    "renderBilling(section, status, transactions, button.dataset.billingPeriod)",
    "renderBilling(section, status, button.dataset.billingPeriod)",
)
source = source.replace(
    "renderBilling(section, updatedStatus, transactions, selectedPeriod)",
    "renderBilling(section, updatedStatus, selectedPeriod)",
)

old_loader = """    const [status, transactionPayload] = await Promise.all([billingFetch('/api/billing/status'), billingFetch('/api/billing/transactions')]);
    renderBilling(section, status, transactionPayload.items || []);"""
new_loader = """    const status = await billingFetch('/api/billing/status');
    renderBilling(section, status);"""
if old_loader not in source:
    raise RuntimeError('Não foi possível localizar a consulta de movimentações do faturamento.')
source = source.replace(old_loader, new_loader, 1)

if '/api/billing/transactions' in source or 'billing-history-section' in source:
    raise RuntimeError('O detalhamento de movimentações ainda está presente após o ajuste.')

path.write_text(source, encoding='utf-8')
