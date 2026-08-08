FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src
COPY data/ data
COPY .env .env
COPY config.py config.py

CMD ["python", "-m src.discord_bot"]