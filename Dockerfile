# Recovery deployment marker: last working frontend build
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
COPY scripts/connect_domnai_chat.py /tmp/connect_domnai_chat.py
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
RUN apk add --no-cache python3 \
    && python3 /tmp/connect_domnai_chat.py \
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
    && npm run build

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY --from=frontend-builder /frontend/dist ./frontend/dist
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]