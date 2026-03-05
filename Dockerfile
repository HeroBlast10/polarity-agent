FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# -- Dependencies (cached layer) ------------------------------------------
COPY pyproject.toml uv.lock* README.md LICENSE ./
COPY src/ src/
RUN uv sync --no-dev --extra web --extra ollama

# -- Application code ------------------------------------------------------
COPY app.py .
COPY AUP.md SECURITY.md ./

ENV POLARITY_PROVIDER=ollama \
    POLARITY_MODEL=llama3 \
    POLARITY_BASE_URL=http://host.docker.internal:11434

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

CMD ["uv", "run", "python", "app.py"]
