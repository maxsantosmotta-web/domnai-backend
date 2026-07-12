FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
COPY scripts/connect_domnai_chat.py /tmp/connect_domnai_chat.py
COPY scripts/connect_operation_to_composer.py /tmp/connect_operation_to_composer.py
COPY scripts/connect_chat_attachments.py /tmp/connect_chat_attachments.py
COPY scripts/connect_billing_back_label.py /tmp/connect_billing_back_label.py
RUN apk add --no-cache python3 \
    && python3 /tmp/connect_domnai_chat.py \
    && python3 /tmp/connect_operation_to_composer.py \
    && python3 /tmp/connect_chat_attachments.py \
    && python3 /tmp/connect_billing_back_label.py \
    && npm run build

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY --from=frontend-builder /frontend/dist ./frontend/dist
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
