# Makefile
.PHONY: run init-db demo-data clean

run:
	uvicorn src.main:app --reload --port 8000

init-db:
	python -c "from src.database import engine; from src.models import Base; Base.metadata.create_all(bind=engine); print('✅ База данных инициализирована')"

demo-data:
	curl -s http://localhost:8000/demo-data > /dev/null && echo "✅ Демо-данные загружены" || echo "⚠️ Запустите сначала 'make run' в другом терминале"

clean:
	rm -f db.sqlite
	rm -rf uploads/*
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

help:
	@echo "make run          — запустить сервер"
	@echo "make init-db      — создать БД"
	@echo "make demo-data    — заполнить демо-данными"
	@echo "make clean        — очистить БД и загрузки"