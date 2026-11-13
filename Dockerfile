FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BLOG_DATA_DIR=/app/data PYTHONPATH=/app/backend
WORKDIR /app
COPY backend/requirements.lock.txt ./backend/requirements.lock.txt
RUN pip install --no-cache-dir -r backend/requirements.lock.txt \
    && groupadd --gid 10001 blog \
    && useradd --uid 10001 --gid blog --create-home blog
COPY --chown=blog:blog backend/app/ ./backend/app/
COPY --chown=blog:blog backend/migrations/ ./backend/migrations/
COPY --chown=blog:blog THIRD_PARTY_LICENSES/ ./THIRD_PARTY_LICENSES/
COPY --from=frontend --chown=blog:blog /build/frontend/dist/ ./frontend/dist/
RUN mkdir -p /app/data/images && chown -R blog:blog /app/data
USER blog
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log", "--no-server-header", "--limit-concurrency", "64", "--backlog", "128", "--timeout-keep-alive", "5", "--ws", "none"]
