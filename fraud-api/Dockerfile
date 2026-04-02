FROM python:3.12-slim

WORKDIR /app

COPY fraud-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/scripts /app/models
COPY scripts/fraud_ml_common.py /app/scripts/fraud_ml_common.py
COPY models/fraud_model.joblib /app/models/fraud_model.joblib
COPY fraud-api/main.py /app/main.py

ENV FRAUD_MODEL_PATH=/app/models/fraud_model.joblib
ENV PORT=8080

EXPOSE 8080
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
