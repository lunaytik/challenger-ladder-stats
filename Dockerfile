FROM ghcr.io/astral-sh/uv:0.11.23-python3.14-alpine

ENV UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY src/ ./src/
COPY main.py ./

CMD ["uv", "run", "python", "main.py"]