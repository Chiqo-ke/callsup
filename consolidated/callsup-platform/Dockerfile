FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CALLSUP_PLATFORM_TLS_REQUIRED=true

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY callsup_platform /app/callsup_platform
COPY tests /app/tests
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "callsup_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]

