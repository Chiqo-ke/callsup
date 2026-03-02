FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8000
CMD ["uvicorn", "src.callsup_knowledge_ops.main:app", "--host", "0.0.0.0", "--port", "8000"]
