FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


WORKDIR /app

COPY pyproject.toml ./.
COPY uv.lock ./.

RUN uv sync --locked  --compile-bytecode


COPY main.py /app
COPY processed_results_THIS/ /app/processed_results_THIS/

EXPOSE 8080
CMD ["uv", "run", "python", "main.py"]


