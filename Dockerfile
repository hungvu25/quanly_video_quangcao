FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIDEO_BOX_DB_PATH=/data/app.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends mpv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py ./run.py

EXPOSE 8080

CMD ["python", "run.py"]
