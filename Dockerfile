FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FREENET_DATA_DIR=/data

WORKDIR /app

RUN mkdir -p /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py core.py ./
COPY protocols ./protocols

EXPOSE 8000

CMD ["python", "main.py"]
