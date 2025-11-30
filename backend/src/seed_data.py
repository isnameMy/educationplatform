# seed_data.py
from sqlalchemy.orm import sessionmaker
from .database import engine, Base
from .models import User, Course, Module, Assignment, Video, Submission, Enrollment
import datetime
import os
import json # <-- Новый импорт

# Создаём сессию
Session = sessionmaker(bind=engine)
db = Session()

# Удаляем старую БД (если есть)
if os.path.exists("../db.sqlite"):
    os.remove("../db.sqlite")

# Создаём все таблицы
Base.metadata.create_all(bind=engine)

# --- Создаём пользователей ---
student = User(email="student@test.com", name="Алиса", role="student")
teacher = User(email="teacher@test.com", name="Борис", role="teacher")
db.add_all([student, teacher])
db.commit() # Чтобы получить ID

# --- Создаём курс ---
course = Course(
    title="Python для анализа данных",
    description="Изучите Python и основные библиотеки для анализа данных: NumPy, Pandas, Matplotlib, Seaborn.",
    tags="python,data,pandas,numpy,matplotlib,seaborn",
    author="Преподаватель К.",
    content="" # Не используем, т.к. контент в модулях
)
db.add(course)
db.commit() # Чтобы получить ID

# --- Создаём модули ---
modules_data = [
    {"title": "Введение в Python и Jupyter", "type": "text", "content": "<h3>Установка Python</h3><p>Установите Python, pip, Jupyter Notebook...</p><h3>Основы синтаксиса</h3><p>Переменные, типы данных, циклы, функции...</p>"},
    {"title": "Библиотека NumPy", "type": "text", "content": "<h3>Создание массивов</h3><p>np.array, np.zeros, np.ones...</p><h3>Операции</h3><p>Индексация, срезы, математика...</p>"},
    {"title": "Практика: NumPy", "type": "assignment", "content": "<h3>Задание 1: NumPy</h3><p>Создайте массив, выполните математические операции, найдите мин/макс, срезайте данные.</p>"},
    {"title": "Библиотека Pandas", "type": "text", "content": "<h3>DataFrame и Series</h3><p>Создание, индексация (loc, iloc)...</p><h3>Чтение CSV</h3><p>pd.read_csv...</p>"},
    {"title": "Практика: Pandas #1", "type": "assignment", "content": "<h3>Задание 2: Pandas</h3><p>Загрузите CSV, выведите первые 5 строк, отфильтруйте по условию, посчитайте статистику.</p>"},
    {"title": "Визуализация с Matplotlib/Seaborn", "type": "text", "content": "<h3>Matplotlib</h3><p>plot, scatter, hist...</p><h3>Seaborn</h3><p>Введение в статистическую визуализацию...</p>"},
    {"title": "Практика: Визуализация", "type": "assignment", "content": "<h3>Задание 3: Визуализация</h3><p>Постройте 2-3 разных графика по данным из предыдущего задания.</p>"},
    {"title": "Очистка данных", "type": "text", "content": "<h3>Обработка NaN</h3><p>dropna, fillna...</p><h3>Удаление дубликатов</h3><p>drop_duplicates...</p>"},
    {"title": "Практика: Очистка данных", "type": "assignment", "content": "<h3>Задание 4: Очистка</h3><p>Возьмите 'грязный' датасет, примените методы очистки.</p>"},
    {"title": "Группировка и агрегация", "type": "text", "content": "<h3>groupby</h3><p>Использование...</p><h3>agg</h3><p>Функции агрегации...</p>"},
    {"title": "Практика: Группировка", "type": "assignment", "content": "<h3>Задание 5: Группировка</h3><p>Сгруппируйте данные по категории, посчитайте агрегаты.</p>"},
    {"title": "Объединение данных (merge/join)", "type": "text", "content": "<h3>pd.merge</h3><p>Соединение таблиц...</p><h3>pd.concat</h3><p>Объединение по осям...</p>"},
    {"title": "Практика: Объединение", "type": "assignment", "content": "<h3>Задание 6: Объединение</h3><p>Объедините 2 CSV-файла по ключу.</p>"},
    {"title": "Введение в анализ", "type": "text", "content": "<h3>Пример анализа</h3><p>Анализ реального датасета...</p><h3>Формулировка гипотез</h3><p>Как задавать вопросы данным...</p>"},
    {"title": "Финальный проект", "type": "assignment", "content": "<h3>Финальный проект</h3><p>Полный цикл анализа: загрузка, очистка, визуализация, выводы.</p>"},
    # НОВЫЕ МОДУЛИ С ВИДЕО
    {"title": "Видео: Введение в Python", "type": "video", "content": ""},
    {"title": "Видео: NumPy", "type": "video", "content": ""},
    {"title": "Видео: Pandas", "type": "video", "content": ""},
    # НОВЫЕ МОДУЛИ С ТЕСТАМИ
    {"title": "Тест: Основы Python", "type": "assignment", "content": ""}, # content не используется для assignment с тестом
    {"title": "Тест: Библиотека NumPy", "type": "assignment", "content": ""}, # content не используется для assignment с тестом
]

modules = []
for i, data in enumerate(modules_data):
    module = Module(
        course_id=course.id,
        title=data["title"],
        type=data["type"],
        content=data.get("content"),
        order=i+1
    )
    modules.append(module)

db.add_all(modules)
db.commit() # Чтобы получить ID модулей

# --- Создаём задания (связанные с модулями типа "assignment") ---
assignments_data = [
    {"module_id": modules[2].id, "title": "ДЗ 1: NumPy", "description": "Создайте массив, выполните операции.", "deadline": datetime.datetime.now() + datetime.timedelta(days=7), "test_data": None},
    {"module_id": modules[4].id, "title": "ДЗ 2: Pandas #1", "description": "Загрузите CSV, отфильтруйте.", "deadline": datetime.datetime.now() + datetime.timedelta(days=14), "test_data": None},
    {"module_id": modules[6].id, "title": "ДЗ 3: Визуализация", "description": "Постройте графики.", "deadline": datetime.datetime.now() + datetime.timedelta(days=21), "test_data": None},
    {"module_id": modules[8].id, "title": "ДЗ 4: Очистка данных", "description": "Обработайте NaN, удалите дубликаты.", "deadline": datetime.datetime.now() + datetime.timedelta(days=28), "test_data": None},
    {"module_id": modules[10].id, "title": "ДЗ 5: Группировка", "description": "Сгруппируйте, посчитайте агрегаты.", "deadline": datetime.datetime.now() + datetime.timedelta(days=35), "test_data": None},
    {"module_id": modules[12].id, "title": "ДЗ 6: Объединение", "description": "Соедините таблицы.", "deadline": datetime.datetime.now() + datetime.timedelta(days=42), "test_data": None},
    {"module_id": modules[14].id, "title": "Финальный проект", "description": "Полный цикл анализа.", "deadline": datetime.datetime.now() + datetime.timedelta(days=50), "test_data": None},
    # ТЕСТЫ
    {"module_id": modules[18].id, "title": "Тест: Основы Python", "description": "Пройдите тест по основам Python.", "deadline": datetime.datetime.now() + datetime.timedelta(days=5), "test_data": json.dumps({
        "questions": [
            {
                "question": "Какой тип данных используется для хранения целых чисел в Python?",
                "options": ["float", "int", "str", "bool"],
                "correct_answer": 1 # Индекс правильного ответа (0-based)
            },
            {
                "question": "Какой оператор используется для определения функции в Python?",
                "options": ["define", "function", "def", "func"],
                "correct_answer": 2
            }
        ]
    })},
    {"module_id": modules[19].id, "title": "Тест: Библиотека NumPy", "description": "Пройдите тест по библиотеке NumPy.", "deadline": datetime.datetime.now() + datetime.timedelta(days=6), "test_data": json.dumps({
        "questions": [
            {
                "question": "Какой тип данных NumPy используется для хранения массивов?",
                "options": ["list", "tuple", "ndarray", "dict"],
                "correct_answer": 2
            },
            {
                "question": "Какая функция NumPy используется для создания массива, заполненного нулями?",
                "options": ["np.one", "np.empty", "np.zeros", "np.full"],
                "correct_answer": 2
            }
        ]
    })},
]

assignments = []
for data in assignments_data: # <-- ИСПРАВЛЕНО: было assignments_
    assignment = Assignment(
        module_id=data["module_id"],
        title=data["title"],
        description=data["description"],
        deadline=data["deadline"],
        test_data=data["test_data"] # <-- Добавляем test_data
    )
    assignments.append(assignment)

db.add_all(assignments)
db.commit()

# --- Создаём видео (связанные с модулями типа "video") ---
# Примеры ссылок из RuTube (вставь реальные ID)
videos_data = [
    {"module_id": modules[15].id, "title": "Видео: Введение в Python", "description": "Установка, Jupyter, основы синтаксиса.", "video_type": "rutube", "video_url": "https://rutube.ru/play/embed/VIDEO_ID_1"}, # ЗАМЕНИТЬ НА РЕАЛЬНЫЙ ID
    {"module_id": modules[16].id, "title": "Видео: NumPy", "description": "Создание массивов, операции.", "video_type": "rutube", "video_url": "https://rutube.ru/play/embed/VIDEO_ID_2"}, # ЗАМЕНИТЬ НА РЕАЛЬНЫЙ ID
    {"module_id": modules[17].id, "title": "Видео: Pandas", "description": "DataFrame, Series, чтение CSV.", "video_type": "rutube", "video_url": "https://rutube.ru/play/embed/VIDEO_ID_3"}, # ЗАМЕНИТЬ НА РЕАЛЬНЫЙ ID
]

videos = []
for data in videos_data: # <-- ИСПРАВЛЕНО: было videos_
    video = Video(
        module_id=data["module_id"],
        title=data["title"],
        description=data["description"],
        video_type=data["video_type"],
        video_url=data["video_url"]
    )
    videos.append(video)

db.add_all(videos)
db.commit()

# --- Создаём запись студента на курс ---
enrollment = Enrollment(user_id=student.id, course_id=course.id, role="student")
db.add(enrollment)
db.commit()

# --- Создаём пример сабмишена с комментариями ---
# Создаём файл с кодом
example_code = """import numpy as np

# Создаём массив
arr = np.array([1, 2, 3, 4, 5])

# Делаем что-то с массивом
result = []
for i in range(len(arr)):
    result.append(arr[i] ** 2)

# Выводим результат
print(result)

# Ошибка: переменная 'data' не определена
print(data)
"""
if not os.path.exists("uploads"):
    os.makedirs("uploads")
with open("uploads/example_code.py", "w", encoding="utf-8") as f:
    f.write(example_code)

submission = Submission(
    assignment_id=assignments[0].id, # ДЗ 1: NumPy
    student_id=student.id,
    file_path="uploads/example_code.py",
    status="reviewed",
    feedback="Хорошая работа, но есть пара замечаний по эффективности.",
    grade=8
)
db.add(submission)
db.commit()

# --- Закрываем сессию ---
db.close()

print("✅ Демо-данные успешно созданы в db.sqlite")