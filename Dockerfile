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

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["uv", "run", "streamlit", "run", "src/polarity_agent/web.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
