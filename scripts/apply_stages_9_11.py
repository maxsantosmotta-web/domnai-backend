from pathlib import Path

# Etapa 9: Feedback disponível apenas para PREMIUM ou administrador.
feedback_path = Path('/app/app/api/feedback.py')
feedback = feedback_path.read_text(encoding='utf-8')
feedback = feedback.replace(
    'from app.models import UserFeedback, UserProfile',
    'from app.models import BillingAccount, UserFeedback, UserProfile',
    1,
)
helper_marker = 'def _require_admin(session: dict) -> str:\n'
helper = '''def _require_feedback_access(db, user_id: str) -> None:\n    if _has_persisted_admin_access(user_id):\n        return\n    account = db.get(BillingAccount, user_id)\n    if account is None or account.plan != "premium" or account.subscription_status not in {"active", "trialing", "past_due"}:\n        raise HTTPException(\n            status_code=403,\n            detail="O módulo Feedback está disponível exclusivamente no plano PREMIUM.",\n        )\n\n\n'''
if helper not in feedback:
    if helper_marker not in feedback:
        raise RuntimeError('Ponto de acesso do Feedback não encontrado.')
    feedback = feedback.replace(helper_marker, helper + helper_marker, 1)
feedback = feedback.replace(
    '    with session_scope() as db:\n        items = list(\n            db.scalars(\n                select(UserFeedback)\n                .where(UserFeedback.user_id == user_id)',
    '    with session_scope() as db:\n        _require_feedback_access(db, user_id)\n        items = list(\n            db.scalars(\n                select(UserFeedback)\n                .where(UserFeedback.user_id == user_id)',
    1,
)
feedback = feedback.replace(
    '    with session_scope() as db:\n        item = UserFeedback(',
    '    with session_scope() as db:\n        _require_feedback_access(db, user_id)\n        item = UserFeedback(',
    1,
)
feedback_path.write_text(feedback, encoding='utf-8')

# Etapa 11: consultar status não pode criar conta financeira.
billing_path = Path('/app/app/api/billing.py')
billing = billing_path.read_text(encoding='utf-8')
old_status = '''@router.get("/status")\ndef billing_status(session: dict = Depends(require_authenticated_user)):\n    user_id = session.get("sub")\n    with session_scope() as db:\n        account = _get_or_create_account(db, user_id)\n        if account.plan == "free_demo":\n            account.plan = "unselected"\n            db.flush()\n        profile = db.get(UserProfile, user_id)\n        payload = _serialize_account(account)\n        payload["profileCompleted"] = bool(profile and profile.completed)\n        return payload\n'''
new_status = '''@router.get("/status")\ndef billing_status(session: dict = Depends(require_authenticated_user)):\n    user_id = session.get("sub")\n    with session_scope() as db:\n        account = db.get(BillingAccount, user_id)\n        profile = db.get(UserProfile, user_id)\n        if account is None:\n            return {\n                "plan": "unselected",\n                "subscriptionStatus": "inactive",\n                "planCredits": 0,\n                "extraCredits": 0,\n                "totalCredits": 0,\n                "premiumActive": False,\n                "currentPeriodEnd": None,\n                "profileCompleted": bool(profile and profile.completed),\n                "financialAccountExists": False,\n            }\n        payload = _serialize_account(account)\n        payload["profileCompleted"] = bool(profile and profile.completed)\n        payload["financialAccountExists"] = True\n        return payload\n'''
if new_status not in billing:
    if old_status not in billing:
        raise RuntimeError('Rota de status financeiro não encontrada.')
    billing = billing.replace(old_status, new_status, 1)
billing_path.write_text(billing, encoding='utf-8')
