from pathlib import Path

models_path = Path('/app/app/models.py')
models = models_path.read_text(encoding='utf-8')
chat_task_model = '''\n\nclass ChatTask(Base):\n    __tablename__ = "chat_tasks"\n\n    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)\n    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)\n    request_json: Mapped[str] = mapped_column(Text, nullable=False)\n    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)\n    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)\n    credit_transaction_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)\n    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)\n    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)\n    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n'''
if 'class ChatTask(Base):' not in models:
    marker = '\n\nclass DiagnosisState(Base):'
    if marker not in models:
        raise RuntimeError('Ponto de inserção do ChatTask não encontrado.')
    models = models.replace(marker, chat_task_model + marker, 1)
models_path.write_text(models, encoding='utf-8')

credit_path = Path('/app/app/services/credit_meter.py')
credit = credit_path.read_text(encoding='utf-8')
credit = credit.replace(
    'def charge_usage(user_id: str, result: MeteredBrainResult) -> dict:',
    'def charge_usage(user_id: str, result: MeteredBrainResult, idempotency_key: str | None = None) -> dict:',
    1,
)
lookup = '''    with session_scope() as db:\n        account = db.get(BillingAccount, user_id)\n'''
replacement = '''    with session_scope() as db:\n        if idempotency_key:\n            existing = db.scalar(\n                __import__("sqlalchemy").select(CreditTransaction).where(\n                    CreditTransaction.stripe_event_id == idempotency_key\n                )\n            )\n            if existing is not None:\n                account = db.get(BillingAccount, user_id)\n                return {\n                    **usage,\n                    "charged_credits": abs(int(existing.amount or 0)),\n                    "admin_exempt": existing.kind == "admin_usage",\n                    "remaining_credits": (account.plan_credits + account.extra_credits) if account else 0,\n                    "idempotentReplay": True,\n                }\n        account = db.get(BillingAccount, user_id)\n'''
if '"idempotentReplay": True' not in credit:
    if lookup not in credit:
        raise RuntimeError('Ponto de idempotência de créditos não encontrado.')
    credit = credit.replace(lookup, replacement, 1)
credit = credit.replace(
    '                description=(\n                    f"Uso administrativo:',
    '                stripe_event_id=idempotency_key,\n                description=(\n                    f"Uso administrativo:',
    1,
)
credit = credit.replace(
    '            description=(\n                f"DomnAI:',
    '            stripe_event_id=idempotency_key,\n            description=(\n                f"DomnAI:',
    1,
)
credit_path.write_text(credit, encoding='utf-8')

main_path = Path('/app/app/main.py')
main = main_path.read_text(encoding='utf-8')
if 'from app.api.chat_tasks import router as chat_tasks_router' not in main:
    main = main.replace(
        'from app.api.chat_state import router as chat_state_router',
        'from app.api.chat_state import router as chat_state_router\nfrom app.api.chat_tasks import router as chat_tasks_router',
        1,
    )
if 'from app.services.chat_task_worker import start_chat_task_worker' not in main:
    main = main.replace(
        'from app.error_monitoring import module_from_path, record_operational_event',
        'from app.error_monitoring import module_from_path, record_operational_event\nfrom app.services.chat_task_worker import start_chat_task_worker',
        1,
    )
if 'app.include_router(chat_tasks_router)' not in main:
    main = main.replace(
        'app.include_router(chat_state_router)',
        'app.include_router(chat_state_router)\napp.include_router(chat_tasks_router)',
        1,
    )
startup = '''\n\n@app.on_event("startup")\ndef start_persistent_chat_worker():\n    start_chat_task_worker()\n'''
if 'def start_persistent_chat_worker()' not in main:
    marker = '\nfrontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"'
    if marker not in main:
        raise RuntimeError('Ponto de startup não encontrado.')
    main = main.replace(marker, startup + marker, 1)
main_path.write_text(main, encoding='utf-8')
