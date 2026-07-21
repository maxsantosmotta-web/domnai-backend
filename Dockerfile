# Recovery deployment marker: last working frontend build
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
COPY scripts/connect_domnai_chat.py /tmp/connect_domnai_chat.py
COPY scripts/add_chat_retry_button.py /tmp/add_chat_retry_button.py
COPY scripts/connect_chat_sources_frontend.py /tmp/connect_chat_sources_frontend.py
COPY scripts/connect_operation_to_composer.py /tmp/connect_operation_to_composer.py
COPY scripts/connect_chat_attachments.py /tmp/connect_chat_attachments.py
COPY scripts/connect_chat_local_deletion.py /tmp/connect_chat_local_deletion.py
COPY scripts/hide_billing_history.py /tmp/hide_billing_history.py
COPY scripts/connect_pdf_report.py /tmp/connect_pdf_report.py
COPY scripts/connect_react_plan_gate.py /tmp/connect_react_plan_gate.py
COPY scripts/connect_standalone_module_rooms.py /tmp/connect_standalone_module_rooms.py
COPY scripts/connect_billing_signout_first_render.py /tmp/connect_billing_signout_first_render.py
COPY scripts/connect_final_independent_room_behavior.py /tmp/connect_final_independent_room_behavior.py
COPY scripts/connect_premium_notice_viewport_center.py /tmp/connect_premium_notice_viewport_center.py
COPY scripts/connect_admin_access_boundary.py /tmp/connect_admin_access_boundary.py
COPY scripts/fix_admin_reload_persistence.py /tmp/fix_admin_reload_persistence.py
COPY scripts/fix_admin_menu_header_layout.py /tmp/fix_admin_menu_header_layout.py
COPY scripts/fix_user_account_footer_block.py /tmp/fix_user_account_footer_block.py
COPY scripts/connect_admin_feedbacks_view.py /tmp/connect_admin_feedbacks_view.py
COPY scripts/refactor_feedback_light_ui.py /tmp/refactor_feedback_light_ui.py
COPY scripts/fix_feedback_back_button.py /tmp/fix_feedback_back_button.py
COPY scripts/append_interaction_button_states.py /tmp/append_interaction_button_states.py
COPY scripts/connect_admin_users_view.py /tmp/connect_admin_users_view.py
COPY scripts/connect_admin_billing_view.py /tmp/connect_admin_billing_view.py
COPY scripts/connect_admin_errors_view.py /tmp/connect_admin_errors_view.py
COPY scripts/connect_admin_audit_view.py /tmp/connect_admin_audit_view.py
COPY scripts/connect_admin_health_view.py /tmp/connect_admin_health_view.py
COPY scripts/finalize_admin_user_navigation.py /tmp/finalize_admin_user_navigation.py
COPY scripts/upgrade_admin_premium_monitor.py /tmp/upgrade_admin_premium_monitor.py
COPY scripts/fix_admin_overview_entry.py /tmp/fix_admin_overview_entry.py
COPY scripts/fix_chat_operation_delivery.py /tmp/fix_chat_operation_delivery.py
COPY scripts/fix_mobile_chat_keyboard.py /tmp/fix_mobile_chat_keyboard.py
COPY scripts/connect_user_sidebar_collapse.py /tmp/connect_user_sidebar_collapse.py
COPY scripts/connect_single_chat_refresh_bottom.py /tmp/connect_single_chat_refresh_bottom.py
COPY scripts/update_help_artifact_credits.py /tmp/update_help_artifact_credits.py
COPY scripts/connect_user_personalization_frontend.py /tmp/connect_user_personalization_frontend.py
COPY scripts/fix_admin_block3.py /tmp/fix_admin_block3.py
COPY scripts/fix_user_block4.py /tmp/fix_user_block4.py
COPY scripts/fix_p2p_audit_findings.py /tmp/fix_p2p_audit_findings.py
COPY scripts/fix_chat_conversation_pdf_regressions.py /tmp/fix_chat_conversation_pdf_regressions.py
COPY scripts/fix_chat_operation_history_atomic.py /tmp/fix_chat_operation_history_atomic.py
COPY scripts/fix_operation_single_click_execution.py /tmp/fix_operation_single_click_execution.py
COPY scripts/fix_operation_boundary_hidden.py /tmp/fix_operation_boundary_hidden.py
COPY scripts/restore_operation_composer_flow.py /tmp/restore_operation_composer_flow.py
COPY scripts/enable_desktop_enter_to_send.py /tmp/enable_desktop_enter_to_send.py
COPY scripts/finalize_natural_conversation_and_artifact_flow.py /tmp/finalize_natural_conversation_and_artifact_flow.py
COPY scripts/validate_frontend_dist.py /tmp/validate_frontend_dist.py
RUN apk add --no-cache python3 \
    && python3 /tmp/connect_domnai_chat.py \
    && python3 /tmp/add_chat_retry_button.py \
    && python3 /tmp/connect_operation_to_composer.py \
    && python3 /tmp/connect_chat_attachments.py \
    && python3 /tmp/connect_chat_local_deletion.py \
    && python3 /tmp/hide_billing_history.py \
    && python3 /tmp/connect_pdf_report.py \
    && python3 /tmp/connect_react_plan_gate.py \
    && python3 /tmp/connect_standalone_module_rooms.py \
    && python3 /tmp/connect_billing_signout_first_render.py \
    && python3 /tmp/connect_final_independent_room_behavior.py \
    && python3 /tmp/connect_premium_notice_viewport_center.py \
    && python3 /tmp/connect_admin_access_boundary.py \
    && python3 /tmp/fix_admin_reload_persistence.py \
    && python3 /tmp/fix_admin_menu_header_layout.py \
    && python3 /tmp/fix_user_account_footer_block.py \
    && python3 /tmp/connect_admin_feedbacks_view.py \
    && python3 /tmp/refactor_feedback_light_ui.py \
    && python3 /tmp/fix_feedback_back_button.py \
    && python3 /tmp/append_interaction_button_states.py \
    && python3 /tmp/connect_admin_users_view.py \
    && python3 /tmp/connect_admin_billing_view.py \
    && python3 /tmp/connect_admin_errors_view.py \
    && python3 /tmp/connect_admin_audit_view.py \
    && python3 /tmp/connect_admin_health_view.py \
    && python3 /tmp/finalize_admin_user_navigation.py \
    && python3 /tmp/upgrade_admin_premium_monitor.py \
    && python3 /tmp/fix_admin_overview_entry.py \
    && python3 /tmp/fix_chat_operation_delivery.py \
    && python3 /tmp/fix_mobile_chat_keyboard.py \
    && python3 /tmp/connect_user_sidebar_collapse.py \
    && python3 /tmp/connect_single_chat_refresh_bottom.py \
    && python3 /tmp/connect_chat_sources_frontend.py \
    && python3 /tmp/update_help_artifact_credits.py \
    && python3 /tmp/connect_user_personalization_frontend.py \
    && python3 /tmp/fix_admin_block3.py \
    && python3 /tmp/fix_user_block4.py \
    && python3 /tmp/fix_p2p_audit_findings.py \
    && python3 /tmp/fix_chat_conversation_pdf_regressions.py \
    && python3 /tmp/fix_chat_operation_history_atomic.py \
    && python3 /tmp/fix_operation_single_click_execution.py \
    && python3 /tmp/fix_operation_boundary_hidden.py \
    && python3 /tmp/restore_operation_composer_flow.py \
    && python3 /tmp/enable_desktop_enter_to_send.py \
    && python3 /tmp/finalize_natural_conversation_and_artifact_flow.py \
    && npm run build \
    && python3 /tmp/validate_frontend_dist.py

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts/connect_chat_sources_backend.py /tmp/connect_chat_sources_backend.py
COPY scripts/connect_user_personalization_backend.py /tmp/connect_user_personalization_backend.py
COPY scripts/connect_conversational_intent_backend.py /tmp/connect_conversational_intent_backend.py
COPY scripts/finalize_artifact_delivery.py /tmp/finalize_artifact_delivery.py
COPY scripts/fix_admin_block3.py /tmp/fix_admin_block3.py
COPY scripts/fix_p2p_audit_findings.py /tmp/fix_p2p_audit_findings.py
COPY scripts/prepare_artifact_exports_compat.py /tmp/prepare_artifact_exports_compat.py
COPY scripts/fix_artifact_exports.py /tmp/fix_artifact_exports.py
COPY scripts/make_artifact_exports_idempotent.py /tmp/make_artifact_exports_idempotent.py
COPY scripts/fix_artifact_wait_for_user.py /tmp/fix_artifact_wait_for_user.py
COPY scripts/fix_chat_history_retention.py /tmp/fix_chat_history_retention.py
COPY scripts/fix_chat_conversation_pdf_regressions.py /tmp/fix_chat_conversation_pdf_regressions.py
COPY scripts/fix_chat_operation_history_atomic.py /tmp/fix_chat_operation_history_atomic.py
COPY scripts/fix_conversation_reasoning_completion.py /tmp/fix_conversation_reasoning_completion.py
COPY scripts/fix_labor_structured_interpretation.py /tmp/fix_labor_structured_interpretation.py
COPY scripts/force_gpt51_text_intelligence.py /tmp/force_gpt51_text_intelligence.py
COPY scripts/enable_progressive_artifact_delivery.py /tmp/enable_progressive_artifact_delivery.py
COPY scripts/finalize_natural_conversation_and_artifact_flow.py /tmp/finalize_natural_conversation_and_artifact_flow.py
COPY scripts/make_runtime_patches_idempotent.py /tmp/make_runtime_patches_idempotent.py
COPY scripts/fix_chat_worker_operation_scope.py /tmp/fix_chat_worker_operation_scope.py
COPY scripts/expose_openai_429_cause.py /tmp/expose_openai_429_cause.py
COPY scripts/validate_labor_final_response.py /tmp/validate_labor_final_response.py
COPY scripts/enforce_vacation_classification_by_dates.py /tmp/enforce_vacation_classification_by_dates.py
COPY scripts/finalize_conversation_integrity.py /tmp/finalize_conversation_integrity.py
COPY scripts/validate_conversation_runtime.py /tmp/validate_conversation_runtime.py
RUN python /tmp/make_runtime_patches_idempotent.py \
    && python -m py_compile /tmp/*.py \
    && python /tmp/connect_chat_sources_backend.py \
    && python /tmp/connect_user_personalization_backend.py \
    && python /tmp/connect_conversational_intent_backend.py \
    && python /tmp/finalize_artifact_delivery.py \
    && python /tmp/fix_admin_block3.py \
    && python /tmp/fix_p2p_audit_findings.py \
    && python /tmp/prepare_artifact_exports_compat.py \
    && python /tmp/make_artifact_exports_idempotent.py \
    && python /tmp/fix_artifact_exports.py \
    && python /tmp/fix_artifact_wait_for_user.py \
    && python /tmp/fix_chat_history_retention.py \
    && python /tmp/fix_chat_conversation_pdf_regressions.py \
    && python /tmp/fix_chat_operation_history_atomic.py \
    && python /tmp/fix_conversation_reasoning_completion.py \
    && python /tmp/fix_labor_structured_interpretation.py \
    && python /tmp/force_gpt51_text_intelligence.py \
    && python /tmp/enable_progressive_artifact_delivery.py \
    && python /tmp/finalize_natural_conversation_and_artifact_flow.py \
    && python /tmp/fix_chat_worker_operation_scope.py \
    && python /tmp/expose_openai_429_cause.py \
    && python /tmp/validate_labor_final_response.py \
    && python /tmp/enforce_vacation_classification_by_dates.py \
    && python /tmp/finalize_conversation_integrity.py \
    && python -m compileall -q app \
    && python /tmp/validate_conversation_runtime.py
COPY --from=frontend-builder /frontend/dist ./frontend/dist
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]