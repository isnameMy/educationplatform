# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Создаём папку для загрузок
RUN mkdir -p frontend/uploads

# Запуск
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]