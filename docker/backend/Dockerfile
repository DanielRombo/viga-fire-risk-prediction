FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["sh", "-c", "python iniciar.py && uvicorn main:app --host 0.0.0.0 --port 8000"]