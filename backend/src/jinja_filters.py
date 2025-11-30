# src/jinja_filters.py
import json

def from_json(value):
    """Парсит JSON-строку в Python-объект."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        # Возвращаем пустой словарь или список, если парсинг не удался
        return {}