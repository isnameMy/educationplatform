# src/main.py
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .database import SessionLocal
from .models import User, Course, Assignment, Submission, Enrollment, Module, Video
from sqlalchemy.orm import joinedload 
from .ml_recommender import SimpleRecommender
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from .jinja_filters import from_json
import json



# Инициализация
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

templates = Jinja2Templates(directory="../frontend/templates")
templates.env.filters['from_json'] = from_json # <-- Регистрируем фильтр


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
    # Используем сессию SQLAlchemy
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()
    return user

# === Роуты ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/auth", response_class=HTMLResponse)
async def register_page(request: Request):
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
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # 🔥 Проверяем: совпадает ли роль?
        if user.role != role:
            db.close()
            return f"""
            <!-- Modal для ошибки -->
            <div class="modal fade show" id="errorModal" tabindex="-1" style="display: block; background: rgba(0,0,0,0.4);">
              <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                  <div class="modal-header border-0 pb-0">
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                  </div>
                  <div class="modal-body text-center py-4">
                    <div class="mb-4">
                      <div class="icon-circle bg-danger text-white mx-auto mb-3" style="width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <i class="bi bi-x-circle fs-1"></i>
                      </div>
                      <h4 class="mb-3">Роль уже занята</h4>
                      <p class="text-muted">
                        Пользователь с email <code>{email}</code> уже зарегистрирован как 
                        <strong class="text-primary">{'студент' if user.role == 'student' else 'преподаватель'}</strong>.
                      </p>
                      <p class="text-muted small mt-3">
                        <i class="bi bi-lightbulb me-1"></i>
                        Используйте другой email или войдите под существующей ролью.
                      </p>
                    </div>
                    <button 
                      type="button" 
                      class="btn btn-lg btn-primary px-5 py-2 mt-2"
                      data-bs-dismiss="modal"
                      hx-get="/" 
                      hx-target="body" 
                      hx-swap="outerHTML"
                    >
                      <i class="bi bi-arrow-left me-2"></i> Вернуться
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <style>
              .icon-circle {{
                background: linear-gradient(135deg, #ef4444, #b91c1c);
              }}
              .modal-content {{
                border-radius: 16px;
              }}
              .modal.fade .modal-dialog {{
                transform: translateY(0);
                transition: transform 0.3s ease, opacity 0.3s ease;
              }}
              @keyframes modalIn {{
                from {{ opacity: 0; transform: scale(0.95); }}
                to {{ opacity: 1; transform: scale(1); }}
              }}
              .modal-content {{
                animation: modalIn 0.3s ease-out;
              }}
            </style>
            
            <script>
              document.getElementById('errorModal').addEventListener('click', function(e) {{
                if (e.target === this) {{
                  htmx.ajax('GET', '/', {{target: 'body', swap: 'outerHTML'}});
                }}
              }});
            </script>
            """

    # Если пользователь новый, или роль совпадает — создаём/логиним
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
    user = get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/", status_code=303)

    # Фильтрация
    if q:
        q = q.strip().lower()
        courses = [c for c in FAKE_COURSES if q in c["title"].lower() or q in c["description"].lower()]
    else:
        courses = FAKE_COURSES

    progress = 3
    total = 5
    recommendations = [
        {"title": "FastAPI + HTMX", "reason": "Вы начали — углубитесь!"},
    ]

    # ✅ ВСЕГДА ВОЗВРАЩАЕМ ПОЛНУЮ СТРАНИЦУ
    return templates.TemplateResponse(
        "student/dashboard.html",
        {
            "request": request,
            "courses": courses,
            "progress": progress,
            "total": total,
            "recommendations": recommendations,
        }
    )
    

@app.get("/student/courses", response_class=HTMLResponse)
async def student_courses(request: Request):
    user = get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    try:
        # Найти ID курсов, на которые записан студент
        enrolled_course_ids = db.query(Enrollment.course_id).filter(Enrollment.user_id == user.id).all()
        enrolled_course_ids = [e[0] for e in enrolled_course_ids] # список ID

        # Получить курсы, на которые записан студент
        enrolled_courses = db.query(Course).filter(Course.id.in_(enrolled_course_ids)).all()

        # Получить все остальные курсы (для поиска/просмотра)
        other_courses = db.query(Course).filter(~Course.id.in_(enrolled_course_ids)).all()
    finally:
        db.close()

    return templates.TemplateResponse(
        "student/courses.html",
        {
            "request": request,
            "user": user,
            "enrolled_courses": enrolled_courses,
            "other_courses": other_courses,
        }
    )

@app.get("/student/course/{course_id}", response_class=HTMLResponse)
async def student_course_detail(request: Request, course_id: int):
    user = get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    try:
        # Проверяем, записан ли студент на курс
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course_id
        ).first()
        if not enrollment:
            return RedirectResponse("/", status_code=303)

        # Получаем курс
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Курс не найден"},
                status_code=404
            )

        # Получаем *все* модули курса, чтобы посчитать прогресс и статистику
        # Загружаем связанные assignment и video, чтобы избежать DetachedInstanceError
        modules = db.query(Module).filter(Module.course_id == course_id).options(
            joinedload(Module.assignment),
            joinedload(Module.video)
        ).order_by(Module.order).all()

        # Подсчёт прогресса: сколько заданий (модулей типа "assignment") проверено
        total_assignment_modules = len([m for m in modules if m.type == "assignment"])
        completed_submissions = 0
        for mod in modules:
            if mod.type == "assignment" and mod.assignment:
                # Найдём сабмишен *этого* студента для этого задания
                student_submission = next((s for s in mod.assignment.submissions if s.student_id == user.id), None)
                if student_submission and student_submission.status == "reviewed":
                    completed_submissions += 1

        progress = completed_submissions
        total = total_assignment_modules

        # Рассчитываем статистику: количество видео, заданий, текстов через БД
        stats = {"videos": 0, "assignments": 0, "texts": 0}
        for mod in modules:
            if mod.type == "video":
                stats["videos"] += 1
            elif mod.type == "assignment":
                stats["assignments"] += 1
            elif mod.type == "text":
                stats["texts"] += 1

        # Найдём *первый* модуль, чтобы можно было сразу перейти к нему
        first_module = modules[0] if modules else None

    finally:
        db.close()

    # Найти рекомендации (если были)
    recommendations = [
        {"title": "Продвинутый курс по безопасности", "reason": "Рекомендуется после завершения"},
    ]

    return templates.TemplateResponse(
        "student/course_detail.html", # <-- Главный шаблон (только сводка)
        {
            "request": request,
            "user": user,
            "course": course,
            "progress": progress,
            "total": total,
            "stats": stats,
            "first_module": first_module, # Передаём первый модуль
        }
    )

@app.get("/student/course/{course_id}/module/{module_id}", response_class=HTMLResponse)
async def student_module_detail(request: Request, course_id: int, module_id: int):
    user = get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    try:
        # Проверяем, записан ли студент на курс
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course_id
        ).first()
        if not enrollment:
            return RedirectResponse("/student/courses", status_code=303)

        # Получаем *все* модули курса, отсортированные по order, чтобы найти prev/next
        # Загружаем связанные assignment и video
        all_modules = db.query(Module).filter(
            Module.course_id == course_id
        ).options(
            joinedload(Module.assignment).joinedload(Assignment.submissions),
            joinedload(Module.video)
        ).order_by(Module.order).all()

        # Найдём текущий модуль в списке
        current_module_index = -1
        current_module = None
        for i, mod in enumerate(all_modules):
            if mod.id == module_id:
                current_module = mod
                current_module_index = i
                break

        if not current_module:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Модуль не найден"},
                status_code=404
            )

        # Получаем курс
        course = current_module.course # Так как модуль уже загружен с курсом

        # Определим предыдущий и следующий модули
        prev_module = all_modules[current_module_index - 1] if current_module_index > 0 else None
        next_module = all_modules[current_module_index + 1] if current_module_index < len(all_modules) - 1 else None

        # Если модуль — задание, получаем сабмишен
        assignment = None
        submission = None
        if current_module.type == "assignment":
            assignment = current_module.assignment # Уже загружен через joinedload
            if assignment:
                # Найдём сабмишен *этого* студента для этого задания
                submission = next((s for s in assignment.submissions if s.student_id == user.id), None)

        # Если модуль — видео, получаем данные видео
        video = current_module.video if current_module.type == "video" else None # Уже загружен через joinedload

    finally:
        db.close()

    return templates.TemplateResponse(
        "student/module_base.html", # <-- Используем обновлённый шаблон
        {
            "request": request,
            "user": user,
            "course": course,
            "module": current_module,
            "prev_module": prev_module,
            "next_module": next_module,
            "assignment": assignment,
            "submission": submission,
            "video": video,
        }
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

    

    
@app.get("/student/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    try:
        # --- НАХОДИМ ЗАДАНИЕ ---
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "Задание не найдено"},
                status_code=404
            )

        # --- НАХОДИМ САБМИШЕН (для *этого* студента и *этого* задания) ---
        submission = db.query(Submission).filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == user.id
        ).first()

        # --- ОБОГАЩАЕМ САБМИШЕН ДАННЫМИ КОДА И КОММЕНТАРИЯМИ (если есть) ---
        if submission and submission.file_path:
            try:
                with open(submission.file_path, "r", encoding="utf-8") as f:
                    code_content = f.read()
                submission.code_content = code_content
                submission.code_lines = code_content.splitlines()

                # Подготавливаем словарь {line_number: comment_data} (пока пусто, добавим позже)
                submission.code_comments_by_line = {}
            except FileNotFoundError:
                submission.code_content = "Файл с кодом не найден."
                submission.code_lines = ["Файл с кодом не найден."]
                submission.code_comments_by_line = {}

    finally:
        db.close()

    return templates.TemplateResponse(
        "student/module_assignment.html",
        {
            "request": request,
            "user": user,
            "assignment": assignment,
            "submission": submission,
        }
    )
    
    
@app.post("/student/submit-test/{assignment_id}", response_class=HTMLResponse)
async def submit_test(request: Request, assignment_id: int, answers: dict = None):
    user = get_current_user(request)
    if not user or user.role != "student":
        return HTMLResponse(content="<div class='alert alert-danger'>Ошибка аутентификации</div>", status_code=403)

    db = SessionLocal()
    try:
        # Проверяем, что задание (тест) существует
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment or not assignment.test_data:
            return HTMLResponse(content="<div class='alert alert-danger'>Тест не найден или не содержит данных</div>", status_code=404)

        # Загружаем тестовые данные
        test_data = json.loads(assignment.test_data)

        # Проверяем, что пришли ответы
        if not answers or 'answers' not in answers:
             return HTMLResponse(content="<div class='alert alert-danger'>Не переданы ответы на тест</div>", status_code=400)

        submitted_answers = answers['answers'] # Ожидаем, что это список индексов ответов [0, 2, ...]

        # Проверяем количество вопросов
        if len(submitted_answers) != len(test_data['questions']):
            return HTMLResponse(content="<div class='alert alert-danger'>Количество переданных ответов не совпадает с количеством вопросов</div>", status_code=400)

        # Подсчёт баллов
        correct_count = 0
        total_questions = len(test_data['questions'])
        for i, question in enumerate(test_data['questions']):
            if submitted_answers[i] == question['correct_answer']:
                correct_count += 1

        grade_percentage = (correct_count / total_questions) * 100

        # Создаём сабмишен в БД (для теста file_path будет None)
        submission = Submission(
            assignment_id=assignment_id,
            student_id=user.id,
            file_path=None, # Для теста
            status="reviewed", # Для теста сразу "проверен"
            feedback=f"Тест пройден. Правильных ответов: {correct_count}/{total_questions}.",
            grade=grade_percentage,
            test_answers=json.dumps(submitted_answers) # Сохраняем ответы студента
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    except json.JSONDecodeError:
        db.rollback()
        return HTMLResponse(content="<div class='alert alert-danger'>Ошибка при разборе данных теста</div>", status_code=500)
    except Exception as e:
        db.rollback()
        # Лучше логировать ошибку: logger.error(f"Error submitting test: {e}")
        return HTMLResponse(content=f"<div class='alert alert-danger'>Ошибка при сохранении: {str(e)}</div>", status_code=500)
    finally:
        db.close()

    # Возвращаем HTML-ответ для HTMX
    return f"""
    <div class="alert alert-success alert-dismissible fade show d-flex align-items-center" role="alert">
      <i class="bi bi-check2-circle fs-4 me-3"></i>
      <div>
        <strong>Тест отправлен!</strong><br>
        <small>Правильных ответов: {correct_count}/{total_questions} ({grade_percentage:.2f}%)</small>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    <script>
      // Скрываем форму после успешной отправки
      document.getElementById('submit-test-form').style.display = 'none';
    </script>
    """

# --- СТАРЫЙ РОУТ ДЛЯ ОТПРАВКИ ФАЙЛА ---
@app.post("/student/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_assignment(
    request: Request,
    assignment_id: int,
    file: UploadFile = File(...)
):
    user = get_current_user(request)
    if not user or user.role != "student":
        return HTMLResponse(content="<div class='alert alert-danger'>Ошибка аутентификации</div>", status_code=403)

    db = SessionLocal()
    try:
        # Проверяем, что задание существует
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment or assignment.test_data: # Убедимся, что это не тест
            return HTMLResponse(content="<div class='alert alert-danger'>Задание не найдено или предназначено для теста</div>, status_code=404")

        # Создаём директорию uploads, если её нет
        if not UPLOAD_DIR.exists():
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Сохраняем файл
        safe_filename = f"{user.id}_{assignment_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = UPLOAD_DIR / safe_filename
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Создаём сабмишен в БД
        submission = Submission(
            assignment_id=assignment_id,
            student_id=user.id,
            file_path=str(filepath),
            status="pending", # Для файла статус pending
            feedback="",
            grade=0
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    except Exception as e:
        db.rollback()
        # Лучше логировать ошибку: logger.error(f"Error submitting assignment: {e}")
        return HTMLResponse(content=f"<div class='alert alert-danger'>Ошибка при сохранении: {str(e)}</div>", status_code=500)
    finally:
        db.close()

    # Возвращаем HTML-ответ для HTMX
    return """
    <div class="alert alert-info alert-dismissible fade show d-flex align-items-center" role="alert">
      <i class="bi bi-hourglass-split fs-4 me-3"></i>
      <div>
        <strong>Работа отправлена на проверку!</strong><br>
        <small>Преподаватель получит уведомление.</small>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    <script>
      // Скрываем форму после успешной отправки
      document.getElementById('submit-assignment-form').style.display = 'none';
    </script>
    """


# Временные данные — замени на БД позже
# --- ГЛОБАЛЬНЫЕ ФЕЙКОВЫЕ ДАННЫЕ ---
FAKE_COURSES = [
    {
        "id": 1,
        "title": "Python для анализа данных",
        "description": "Изучите Python и основные библиотеки для анализа данных: NumPy, Pandas, Matplotlib, Seaborn.",
        "tags": ["python", "data", "pandas", "numpy", "matplotlib", "seaborn"],
        "author": "Преподаватель К.",
        "modules": [ # 15 модулей, как запланировано
            {
                "id": 1,
                "title": "Введение в Python и Jupyter",
                "type": "text",
                "content": "<h3>Установка Python</h3><p>Установите Python, pip, Jupyter Notebook...</p><h3>Основы синтаксиса</h3><p>Переменные, типы данных, циклы, функции...</p>"
            },
            {
                "id": 2,
                "title": "Библиотека NumPy",
                "type": "text",
                "content": "<h3>Создание массивов</h3><p>np.array, np.zeros, np.ones...</p><h3>Операции</h3><p>Индексация, срезы, математика...</p>"
            },
            {
                "id": 3,
                "title": "Практика: NumPy",
                "type": "assignment",
                "content": "<h3>Задание 1: NumPy</h3><p>Создайте массив, выполните математические операции, найдите мин/макс, срезайте данные.</p>",
                "assignment_id": 1
            },
            {
                "id": 4,
                "title": "Библиотека Pandas",
                "type": "text",
                "content": "<h3>DataFrame и Series</h3><p>Создание, индексация (loc, iloc)...</p><h3>Чтение CSV</h3><p>pd.read_csv...</p>"
            },
            {
                "id": 5,
                "title": "Практика: Pandas #1",
                "type": "assignment",
                "content": "<h3>Задание 2: Pandas</h3><p>Загрузите CSV, выведите первые 5 строк, отфильтруйте по условию, посчитайте статистику.</p>",
                "assignment_id": 2
            },
            {
                "id": 6,
                "title": "Визуализация с Matplotlib/Seaborn",
                "type": "text",
                "content": "<h3>Matplotlib</h3><p>plot, scatter, hist...</p><h3>Seaborn</h3><p>Введение в статистическую визуализацию...</p>"
            },
            {
                "id": 7,
                "title": "Практика: Визуализация",
                "type": "assignment",
                "content": "<h3>Задание 3: Визуализация</h3><p>Постройте 2-3 разных графика по данным из предыдущего задания.</p>",
                "assignment_id": 3
            },
            {
                "id": 8,
                "title": "Очистка данных",
                "type": "text",
                "content": "<h3>Обработка NaN</h3><p>dropna, fillna...</p><h3>Удаление дубликатов</h3><p>drop_duplicates...</p>"
            },
            {
                "id": 9,
                "title": "Практика: Очистка данных",
                "type": "assignment",
                "content": "<h3>Задание 4: Очистка</h3><p>Возьмите 'грязный' датасет, примените методы очистки.</p>",
                "assignment_id": 4
            },
            {
                "id": 10,
                "title": "Группировка и агрегация",
                "type": "text",
                "content": "<h3>groupby</h3><p>Использование...</p><h3>agg</h3><p>Функции агрегации...</p>"
            },
            {
                "id": 11,
                "title": "Практика: Группировка",
                "type": "assignment",
                "content": "<h3>Задание 5: Группировка</h3><p>Сгруппируйте данные по категории, посчитайте агрегаты.</p>",
                "assignment_id": 5
            },
            {
                "id": 12,
                "title": "Объединение данных (merge/join)",
                "type": "text",
                "content": "<h3>pd.merge</h3><p>Соединение таблиц...</p><h3>pd.concat</h3><p>Объединение по осям...</p>"
            },
            {
                "id": 13,
                "title": "Практика: Объединение",
                "type": "assignment",
                "content": "<h3>Задание 6: Объединение</h3><p>Объедините 2 CSV-файла по ключу.</p>",
                "assignment_id": 6
            },
            {
                "id": 14,
                "title": "Введение в анализ",
                "type": "text",
                "content": "<h3>Пример анализа</h3><p>Анализ реального датасета...</p><h3>Формулировка гипотез</h3><p>Как задавать вопросы данным...</p>"
            },
            {
                "id": 15,
                "title": "Финальный проект",
                "type": "assignment",
                "content": "<h3>Финальный проект</h3><p>Полный цикл анализа: загрузка, очистка, визуализация, выводы.</p>",
                "assignment_id": 7
            }
        ]
    },
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

FAKE_VIDEOS = [
    {
        "id": 1,
        "course_id": 1,
        "title": "Видео: Введение в Python",
        "description": "Установка, Jupyter, основы синтаксиса.",
        "video_type": "youtube",
        "video_url": "https://www.youtube.com/watch?v=8DvywoWv6fI" # Пример из предыдущего сообщения
    },
    {
        "id": 2,
        "course_id": 1,
        "title": "Видео: NumPy",
        "description": "Создание массивов, операции.",
        "video_type": "youtube",
        "video_url": "https://www.youtube.com/watch?v=QUT1VHi_EJY"
    },
    {
        "id": 3,
        "course_id": 1,
        "title": "Видео: Pandas",
        "description": "DataFrame, Series, чтение CSV.",
        "video_type": "youtube",
        "video_url": "https://www.youtube.com/watch?v=vmEHCJofslg"
    },
]

