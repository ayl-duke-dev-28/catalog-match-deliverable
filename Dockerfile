FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CATALOG_MATCH_HOST=0.0.0.0
ENV CATALOG_MATCH_PORT=8000

WORKDIR /app

COPY app.py .
COPY catalog_match ./catalog_match
COPY static ./static
COPY catalog.csv .
COPY order-history.csv .

EXPOSE 8000

CMD ["python", "app.py"]
