FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv
COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY seed ./seed
COPY migrations ./migrations
RUN pip install --no-cache-dir .

EXPOSE 8001
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8001"]
