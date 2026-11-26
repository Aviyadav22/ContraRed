FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 app && chown -R app /app
USER app

CMD ["sh", "-c", "uvicorn main:app --host 127.0.0.1 --port ${PORT:-8100} --proxy-headers --forwarded-allow-ips 127.0.0.1 --log-level info"]
