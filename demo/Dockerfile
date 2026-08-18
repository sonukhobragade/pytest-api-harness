FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir \
      fastapi==0.115.6 uvicorn==0.34.0 psycopg2-binary==2.9.10 \
      redis==5.2.1 pydantic==2.10.4
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
