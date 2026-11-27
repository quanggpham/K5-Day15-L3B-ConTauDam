FROM node:22-bookworm-slim AS frontend
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.7.0 --activate
COPY codebase/frontend/package.json codebase/frontend/pnpm-lock.yaml codebase/frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY codebase/frontend/ ./
RUN pnpm build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY codebase/ ./codebase/
COPY --from=frontend /app/dist ./codebase/frontend/dist
CMD ["sh", "-c", "uvicorn codebase.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
