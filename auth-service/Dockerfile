
FROM python:3.12-slim

# Встановлення робочої директорії
WORKDIR /app

# Копіювання файлу залежностей
COPY requirements.txt .

# Встановлення програмних залежностей
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання файлів мікросервісу
COPY . .

# Внутрішній порт мікросервісу
EXPOSE 8000

# Запуск застосунку FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
