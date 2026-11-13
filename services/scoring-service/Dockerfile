FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir poetry==2.0.1
COPY pyproject.toml ./
COPY ../../shared-contracts /shared-contracts
RUN poetry config virtualenvs.create false && poetry install --only=main --no-root

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build /usr/local/bin /usr/local/bin
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd -m app && chown -R app /app
USER app
EXPOSE 8002
CMD ["uvicorn", "scoring.main:app", "--host", "0.0.0.0", "--port", "8002"]
