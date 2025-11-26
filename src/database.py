# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# Используем SQLite — 1 файл, не нужен сервер
SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # для SQLite в одном потоке
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаём таблицы при первом запуске
Base.metadata.create_all(bind=engine)