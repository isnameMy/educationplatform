# src/main.py
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .database import SessionLocal
from .models import User, Course, Assignment, Submission, Material
from .ml_recommender import SimpleRecommender
import os
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request




# Инициализация
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

templates = Jinja2Templates(directory="../frontend/templates")


# Папки
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Раздаём статику и загрузки
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
app.mount("/uploads", StaticFiles(directory="../frontend/uploads"), name="uploads")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return user

# === Роуты ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(f"/{user.role}/dashboard", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})

# --- Регистрация ---
@app.post("/set-role", response_class=HTMLResponse)
async def set_role(request: Request, role: str = Form(...)):
    request.session["temp_role"] = role
    icon = "mortarboard" if role == "student" else "person-workspace"
    title = "Студент" if role == "student" else "Преподаватель"
    return f"""
    <div class="alert alert-info d-flex align-items-center">
      <i class="bi bi-{icon} fs-4 me-3"></i>
      <div>
        <h5>Вы выбрали: <strong>{title}</strong></h5>
        <p class="mb-0">Введите email для завершения регистрации</p>
      </div>
    </div>
    <form hx-post="/register" hx-target="body" hx-swap="outerHTML" class="mt-3">
      <input type="hidden" name="role" value="{role}">
      <div class="mb-3">
        <label class="form-label">Ваш email</label>
        <input type="email" name="email" class="form-control" required placeholder="ivan@example.com">
      </div>
      <button type="submit" class="btn btn-success w-100 py-2">
        <i class="bi bi-check-circle me-2"></i> Завершить регистрацию
      </button>
    </form>
    """

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, email: str = Form(...), role: str = Form(...)):
    db = SessionLocal()
    # Проверяем, есть ли уже
    user = db.query(User).filter(User.email == email).first()
    if not user:
        name = email.split("@")[0].title()
        user = User(email=email, name=name, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Сохраняем в сессии
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_role"] = user.role
    
    db.close()
    return RedirectResponse(f"/{user.role}/dashboard", status_code=303)

# --- Студент ---
@app.get("/student/dashboard", response_class=HTMLResponse)
async def student_dashboard(request: Request, q: str = None):
    if q:
        q = q.lower()
        courses = [
            c for c in FAKE_COURSES
            if q in c["title"].lower() or q in c["description"].lower()
        ]
    else:
        courses = FAKE_COURSES

    return templates.TemplateResponse(
        "student/dashboard.html",
        {"request": request, "courses": courses}
    )

import datetime

@app.get("/student/course/{course_id}", response_class=HTMLResponse)
async def student_course_detail(request: Request, course_id: int):
    # Ищем курс в общем списке
    course = next((c for c in FAKE_COURSES if c["id"] == course_id), None)
    if not course:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Курс не найден"},
            status_code=404
        )

    assignments = FAKE_ASSIGNMENTS.get(course_id, [])
    submissions = {}
    for aid, sub in FAKE_SUBMISSIONS.items():
        if aid in [a["id"] for a in assignments]:
            # Гарантируем, что есть submitted_at
            sub_copy = sub.copy()
            if "submitted_at" not in sub_copy:
                sub_copy["submitted_at"] = datetime.datetime.now().strftime("%Y-%m-%d")
            submissions[aid] = sub_copy

    total = len(assignments)
    progress = len([s for s in submissions.values() if s["status"] == "reviewed"])

    recommendations = [
        {"title": "Продвинутый курс по безопасности", "reason": "Рекомендуется после завершения"},
    ]

    return templates.TemplateResponse(
        "student/course_detail.html",
        {
            "request": request,
            "course": course,
            "progress": progress,
            "total": total,
            "assignments": assignments,
            "submissions": submissions,
            "recommendations": recommendations,
        }
    )

@app.get("/student/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    # --- НАХОДИМ ЗАДАНИЕ ---
    assignment = None
    course_id = None
    for cid, assigns in FAKE_ASSIGNMENTS.items():
        for a in assigns:
            if a["id"] == assignment_id:
                assignment = a
                course_id = cid
                break
        if assignment:
            break

    if not assignment:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Задание не найдено"},
            status_code=404
        )

    # --- НАХОДИМ САБМИШЕН ---
    submission = FAKE_SUBMISSIONS.get(assignment_id)

    # --- ПЕРЕДАЁМ В ТВОЙ ШАБЛОН ---
    return templates.TemplateResponse(
        "student/assignment.html",  # ← твой файл!
        {
            "request": request,
            "assignment": assignment,
            "submission": submission,
            # Если в шаблоне нужен course_id для "назад" — раскомментируй:
            # "course_id": course_id
        }
    )

@app.get("/student/course/{course_id}/material", response_class=HTMLResponse)
async def course_material(request: Request, course_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    # Найти курс
    course = next((c for c in FAKE_COURSES if c["id"] == course_id), None)
    if not course:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Курс не найден"},
            status_code=404
        )

    # Добавь content, если хочешь (пока хардкод)
    course["content"] = """
        <h2>Введение в тему</h2>
        <p>Это учебный материал курса. Тут может быть HTML, формулы, код и т.д.</p>
        <pre><code>print("Hello, coal!")</code></pre>
    """

    return templates.TemplateResponse(
        "student/course_material.html",
        {"request": request, "course": course}
    )

  
# --- Преподаватель ---
@app.get("/teacher/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    user = get_current_user(request)
    if not user or user.role != "teacher":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    pending = (
        db.query(Submission)
        .filter(Submission.status == "pending")
        .join(Assignment)
        .join(User, User.id == Submission.student_id)
        .all()
    )
    db.close()

    return templates.TemplateResponse(
        "teacher/dashboard.html",
        {"request": request, "submissions": pending}
    )

@app.get("/teacher/review/{submission_id}", response_class=HTMLResponse)
async def review_page(request: Request, submission_id: int):
    user = get_current_user(request)
    if not user or user.role != "teacher":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    submission = (
        db.query(Submission)
        .filter(Submission.id == submission_id)
        .join(Assignment)
        .join(User, User.id == Submission.student_id)
        .first()
    )
    db.close()

    if not submission:
        return HTMLResponse("<div class='alert alert-danger'>Работа не найдена</div>")

    return templates.TemplateResponse(
        "teacher/review.html",
        {"request": request, "submission": submission}
    )

@app.post("/teacher/review/{submission_id}", response_class=HTMLResponse)
async def submit_review(
    request: Request,
    submission_id: int,
    grade: int = Form(...),
    feedback: str = Form("")
):
    db = SessionLocal()
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(404)

    submission.grade = grade
    submission.feedback = feedback
    submission.status = "reviewed"
    db.commit()
    db.close()

    return """
    <div class="alert alert-success alert-dismissible fade show d-flex align-items-center" role="alert">
      <i class="bi bi-check2-circle fs-4 me-3"></i>
      <div>
        <strong>Работа проверена!</strong><br>
        <small>Студент получит уведомление при следующем заходе.</small>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    """

# --- Вспомогательные ---
@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/demo-data", response_class=HTMLResponse)
async def demo_data():
    """Для быстрого заполнения БД (make demo-data)"""
    db = SessionLocal()
    
    # Чистим
    db.query(Submission).delete()
    db.query(Assignment).delete()
    db.query(Course).delete()
    db.query(User).delete()
    
    # Пользователи
    student = User(email="student@test.com", name="Алиса", role="student")
    teacher = User(email="teacher@test.com", name="Борис", role="teacher")
    db.add_all([student, teacher])
    db.commit()
    


    



# Временные данные — замени на БД позже
# --- ГЛОБАЛЬНЫЕ ФЕЙКОВЫЕ ДАННЫЕ ---
FAKE_COURSES = [
    {"id": 1, "title": "Основы самовозгорания угля", "description": "Научись предсказывать пожары на шахтах"},
    {"id": 2, "title": "React для чайников", "description": "С нуля до хакатона за 2 часа"},
    {"id": 3, "title": "FastAPI + HTMX", "description": "Создай веб-сервис без боли"},
    {"id": 4, "title": "ML для угольной промышленности", "description": "Предсказание рисков с нейросетями"},
    {"id": 5, "title": "Безопасность в горных выработках", "description": "Методы предотвращения обвалов и взрывов"},
    {"id": 6, "title": "Python для анализа данных", "description": "Pandas, NumPy, визуализация"},
    {"id": 7, "title": "Основы вентиляции шахт", "description": "Контроль газа и температуры под землёй"},
    {"id": 8, "title": "Docker для разработчиков", "description": "Контейнеризация от новичка до профи"},
    {"id": 9, "title": "Механика горных пород", "description": "Изучение прочности и деформации массивов"},
    {"id": 10, "title": "SQL и реляционные БД", "description": "От SELECT до сложных JOIN'ов"},
    {"id": 11, "title": "Автоматизация добычи угля", "description": "Роботы, дроны и умные системы"},
    {"id": 12, "title": "Git и управление версиями", "description": "Работа в команде без конфликтов"},
    {"id": 13, "title": "Теплообмен в угольных пластах", "description": "Физические модели самовозгорания"},
    {"id": 14, "title": "TypeScript в реальных проектах", "description": "Типизация, интерфейсы, продакшен"},
    {"id": 15, "title": "Геоинформационные системы (ГИС)", "description": "Картография для горной промышленности"},
    {"id": 16, "title": "REST API: design и best practices", "description": "Как проектировать API, которым приятно пользоваться"},
    {"id": 17, "title": "Экология добычи полезных ископаемых", "description": "Снижение ущерба окружающей среде"},
    {"id": 18, "title": "PostgreSQL для бэкенд-разработки", "description": "Индексы, транзакции, оптимизация"},
    {"id": 19, "title": "Сенсорные сети для мониторинга шахт", "description": "IoT в условиях высокой опасности"},
    {"id": 20, "title": "Алгоритмы и структуры данных", "description": "База для всех олимпиад и собесов"},
    {"id": 21, "title": "Метановый контроль на шахтах", "description": "Детекция и предотвращение взрывов"},
    {"id": 22, "title": "Тестирование на Python (pytest)", "description": "Unit, integration, mocking"},
    {"id": 23, "title": "Гидрогеология угольных месторождений", "description": "Влияние воды на устойчивость пластов"},
    {"id": 24, "title": "Frontend Performance Optimization", "description": "Как ускорить сайт до 90+ в Lighthouse"},
    {"id": 25, "title": "Экономика горного производства", "description": "Рентабельность, затраты, ROI"},
    {"id": 26, "title": "Аутентификация и авторизация", "description": "JWT, OAuth2, сессии, безопасность"},
    {"id": 27, "title": "Моделирование рисков в добыче", "description": "Monte Carlo, сценарный анализ"},
    {"id": 28, "title": "Linux для бэкенд-разработчика", "description": "Команды, процессы, сети, bash"},
    {"id": 29, "title": "Транспорт угля: логистика и автоматизация", "description": "От забоя до порта"},
    {"id": 30, "title": "Асинхронный Python (async/await)", "description": "FastAPI, aiohttp, производительность"},
    {"id": 31, "title": "История угольной промышленности", "description": "От паровых машин до умных шахт"},
    {"id": 32, "title": "CSS Grid и Flexbox", "description": "Макеты без бутстрапа"},
    {"id": 33, "title": "Оценка запасов угля", "description": "Геологоразведка и подсчёт ресурсов"},
    {"id": 34, "title": "WebSocket и реалтайм", "description": "Чаты, уведомления, дашборды"},
    {"id": 35, "title": "Правила техники безопасности на шахтах", "description": "ГОСТы, инструктажи, экипировка"},
    {"id": 36, "title": "Запуск MVP за выходные", "description": "HTMX, FastAPI, SQLite — без боли"},
    {"id": 37, "title": "Геомеханика массивов горных пород", "description": "Прогноз устойчивости выработок"},
    {"id": 38, "title": "React Query и управление состоянием", "description": "Забудь про Redux"},
    {"id": 39, "title": "Переработка угля: коксование и газификация", "description": "От сырья до химии"},
    {"id": 40, "title": "Миграции и Alembic", "description": "Управление схемой БД в FastAPI"},
    {"id": 41, "title": "Энергосбережение в горной промышленности", "description": "Снижение затрат на вентиляцию и подъём"},
    {"id": 42, "title": "Deploy FastAPI на сервер", "description": "Nginx, Gunicorn, systemd, HTTPS"},
    {"id": 43, "title": "Подземная геофизика", "description": "Сейсморазведка и каротаж"},
    {"id": 44, "title": "Jinja2 и серверный рендеринг", "description": "SEO-friendly интерфейсы без JS"},
    {"id": 45, "title": "Углеродный след добычи", "description": "Углеродный аудит и компенсации"},
    {"id": 46, "title": "CI/CD для веб-проектов", "description": "GitHub Actions, тесты, деплой"},
    {"id": 47, "title": "Открытые данные о добыче", "description": "Росстат, US Energy, API"},
    {"id": 48, "title": "Оптимизация запросов к БД", "description": "EXPLAIN, индексы, N+1 проблема"},
    {"id": 49, "title": "Цифровой двойник шахты", "description": "BIM, 3D-модели, IoT-интеграция"},
    {"id": 50, "title": "Как выиграть хакатон по горной тематике", "description": "Идеи, командная работа, презентация"},
]
FAKE_ASSIGNMENTS = {
    1: [{"id": 101, "title": "Анализ температуры", "description": "Собери данные с датчиков"}],
    2: [{"id": 201, "title": "Первый компонент", "description": "Создай кнопку в React"}],
    3: [{"id": 301, "title": "Создай API", "description": "Напиши GET-эндпоинт"}],
    4: [{"id": 401, "title": "Обучи модель", "description": "Используй данные по углям"}],
    5: [{"id": 501, "title": "Оценка риска обвала", "description": "Рассчитай коэффициент устойчивости"}],
    6: [{"id": 601, "title": "Анализ данных в Pandas", "description": "Очисти и визуализируй датасет"}],
    7: [{"id": 701, "title": "Моделирование вентиляции", "description": "Спроектируй систему воздухообмена"}],
    8: [{"id": 801, "title": "Создай Dockerfile", "description": "Упакуй приложение в контейнер"}],
    9: [{"id": 901, "title": "Анализ прочности пород", "description": "Оцени напряжения в массиве"}],
    10: [{"id": 1001, "title": "Сложный SQL-запрос", "description": "Напиши запрос с 3 JOIN'ами и агрегацией"}],
    11: [{"id": 1101, "title": "Дизайн автоматизированной системы", "description": "Опиши архитектуру роботизированной добычи"}],
    12: [{"id": 1201, "title": "Работа с ветками в Git", "description": "Создай feature-ветку и сделай PR"}],
    13: [{"id": 1301, "title": "Тепловой расчёт", "description": "Смоделируй накопление тепла в угле"}],
    14: [{"id": 1401, "title": "Типизация компонента", "description": "Добавь TypeScript к существующему коду"}],
    15: [{"id": 1501, "title": "Создание карты месторождения", "description": "Используй QGIS или аналог"}],
    16: [{"id": 1601, "title": "Проектирование REST API", "description": "Спроектируй эндпоинты для курса"}],
    17: [{"id": 1701, "title": "Экологический аудит", "description": "Оцени воздействие на флору и фауну"}],
    18: [{"id": 1801, "title": "Оптимизация запроса", "description": "Ускори медленный SQL-запрос в 10 раз"}],
    19: [{"id": 1901, "title": "Дизайн сенсорной сети", "description": "Размести датчики по шахте для покрытия"}],
    20: [{"id": 2001, "title": "Реализация хеш-таблицы", "description": "Напиши свою структуру данных на Python"}],
    21: [{"id": 2101, "title": "Анализ концентрации метана", "description": "Построй график изменения по времени"}],
    22: [{"id": 2201, "title": "Напиши unit-тесты", "description": "Покрой основную логику тестами"}],
    23: [{"id": 2301, "title": "Гидрогеологический отчёт", "description": "Оцени влияние грунтовых вод"}],
    24: [{"id": 2401, "title": "Оптимизация изображений", "description": "Сожми картинки без потери качества"}],
    25: [{"id": 2501, "title": "Расчёт рентабельности", "description": "Посчитай окупаемость проекта"}],
    26: [{"id": 2601, "title": "Реализация JWT-авторизации", "description": "Добавь защиту к API"}],
    27: [{"id": 2701, "title": "Моделирование рисков", "description": "Проведи анализ сценариев в Excel"}],
    28: [{"id": 2801, "title": "Напиши bash-скрипт", "description": "Автоматизируй развёртывание"}],
    29: [{"id": 2901, "title": "Оптимизация логистики", "description": "Снизь затраты на транспортировку"}],
    30: [{"id": 3001, "title": "Асинхронный эндпоинт", "description": "Реализуй обработку без блокировки"}],
    31: [{"id": 3101, "title": "Исторический обзор", "description": "Напиши эссе о развитии промышленности"}],
    32: [{"id": 3201, "title": "Адаптивная вёрстка", "description": "Сделай макет для мобильных"}],
    33: [{"id": 3301, "title": "Оценка запасов", "description": "Рассчитай объём угля по данным бурения"}],
    34: [{"id": 3401, "title": "Реалтайм-чат", "description": "Добавь WebSocket-уведомления"}],
    35: [{"id": 3501, "title": "Инструктаж по ТБ", "description": "Создай чек-лист для новых сотрудников"}],
    36: [{"id": 3601, "title": "Сборка MVP", "description": "Сделай рабочий прототип за 4 часа"}],
    37: [{"id": 3701, "title": "Геомеханический расчёт", "description": "Оцени устойчивость выработки"}],
    38: [{"id": 3801, "title": "Интеграция React Query", "description": "Замени ручные fetch'и на хуки"}],
    39: [{"id": 3901, "title": "Технологическая схема", "description": "Нарисуй процесс переработки угля"}],
    40: [{"id": 4001, "title": "Настройка миграций", "description": "Создай Alembic-миграцию для новой таблицы"}],
    41: [{"id": 4101, "title": "Аудит энергопотребления", "description": "Найди точки для снижения затрат"}],
    42: [{"id": 4201, "title": "Деплой на сервер", "description": "Настрой Nginx и Gunicorn"}],
    43: [{"id": 4301, "title": "Интерпретация сейсмоданных", "description": "Выяви аномалии в массиве"}],
    44: [{"id": 4401, "title": "Серверный рендеринг", "description": "Сделай SEO-дружественную страницу"}],
    45: [{"id": 4501, "title": "Углеродный баланс", "description": "Рассчитай CO2-эмиссию процесса"}],
    46: [{"id": 4601, "title": "GitHub Actions", "description": "Настрой CI для запуска тестов"}],
    47: [{"id": 4701, "title": "Анализ открытых данных", "description": "Используй API Росстата для отчёта"}],
    48: [{"id": 4801, "title": "Индексация таблицы", "description": "Ускорь запрос с помощью индекса"}],
    49: [{"id": 4901, "title": "3D-модель шахты", "description": "Создай цифровой двойник в Blender"}],
    50: [{"id": 5001, "title": "Подготовка демо", "description": "Собери презентацию для жюри хакатона"}],
}


FAKE_SUBMISSIONS = {
    1: [{"id": 101, "title": "Анализ температуры", "description": "Собери данные с датчиков"}],
}