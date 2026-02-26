FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для быстродействия
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY bot.py .
COPY questions/ ./questions/

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health')" || exit 1

CMD ["python", "bot.py"]
