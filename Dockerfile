# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY backend/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код проекта внутрь контейнера
COPY . .

# Указываем команду запуска приложения
# Сначала запускаем скрипт seed_data.py (теперь внутри папки src), затем запускаем Uvicorn
# Используем &&, чтобы Uvicorn запустился только если seed_data.py завершился успешно
# CMD ["sh", "-c", "python -m src.seed_data && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"]

# АЛЬТЕРНАТИВА: Если python -m src.seed_data не работает из-за __main__.py, используйте:
CMD ["sh", "-c", "python -m backend.src.seed_data && uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload"]

# Если хочешь отключить --reload в продакшене (рекомендуется), используй:
# CMD ["sh", "-c", "python src/seed_data.py && uvicorn src.main:app --host 0.0.0.0 --port 8000"]