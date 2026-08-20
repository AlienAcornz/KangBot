FROM python:3.13.2-slim

WORKDIR /app

COPY requirements.txt .

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "src.discord_bot"]