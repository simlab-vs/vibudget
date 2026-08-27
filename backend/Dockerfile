# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /src

# Install the dependencies against a stub package so this layer is only rebuilt
# when pyproject.toml changes, then install the real sources on top of it.
COPY pyproject.toml ./
RUN mkdir -p vibudget && touch vibudget/__init__.py \
    && uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python .

COPY vibudget ./vibudget
RUN uv pip install --python /opt/venv/bin/python --no-deps .


FROM builder AS dev-builder

RUN uv pip install --python /opt/venv/bin/python ".[dev]"


FROM python:3.12-slim-bookworm AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 1000 vibudget
COPY --from=builder /opt/venv /opt/venv

USER vibudget
WORKDIR /app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request as r; r.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["vibudget", "serve", "--host", "0.0.0.0", "--port", "8000"]


# Adds pytest, httpx and ruff, plus the pyproject.toml that configures them.
FROM runtime AS dev

COPY --from=dev-builder /opt/venv /opt/venv
COPY pyproject.toml ./
COPY tests ./tests
