FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app

COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app src ./src

RUN chown app:app /app

USER app

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "rag_system.main"]