# src/main.py
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from .database import SessionLocal
from .models import User, Course, Assignment, Submission
from .ml_recommender import SimpleRecommender
import os
import shutil
from pathlib import Path
from datetime import datetime

# Инициализация
app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

templates = Jinja2Templates(directory="src/templates")

# Папки
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Раздаём статику и загрузки
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Вспомогательные функции
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
async def student_dashboard(request: Request):
    user = get_current_user(request)
    if not user or user.role != "student":
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    
    # Гарантируем, что есть хотя бы 1 курс
    if db.query(Course).count() == 0:
        course = Course(
            title="Введение в машинное обучение",
            description="Курс для начинающих: линейная регрессия, классификация, scikit-learn",
            tags="ml,python,math"
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        
        # Добавляем задания
        assignments = [
            Assignment(course_id=course.id, title="ДЗ 1: Линейная регрессия", description="Реализуйте на Python"),
            Assignment(course_id=course.id, title="ДЗ 2: Классификация", description="Используйте scikit-learn"),
            Assignment(course_id=course.id, title="ДЗ 3: Валидация", description="Кросс-валидация и метрики"),
        ]
        db.add_all(assignments)
        db.commit()

    # Данные для студента
    course = db.query(Course).first()
    assignments = db.query(Assignment).filter(Assignment.course_id == course.id).all()
    submissions = {s.assignment_id: s for s in db.query(Submission).filter(Submission.student_id == user.id).all()}
    
    completed = [a.id for a in assignments if submissions.get(a.id) and submissions[a.id].status == "reviewed"]
    progress = len(completed)
    total = len(assignments)

    # Рекомендации
    recommender = SimpleRecommender()
    recommendations = recommender.recommend_for_user(completed)

    db.close()

    return templates.TemplateResponse(
        "student/dashboard.html",
        {
            "request": request,
            "user": user,
            "course": course,
            "assignments": assignments,
            "submissions": submissions,
            "progress": progress,
            "total": total,
            "recommendations": recommendations,
        }
    )

@app.get("/student/assignment/{assignment_id}", response_class=HTMLResponse)
async def student_assignment(request: Request, assignment_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == user.id
    ).first()
    db.close()

    return templates.TemplateResponse(
        "student/assignment.html",
        {"request": request, "assignment": assignment, "submission": submission}
    )

@app.post("/student/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_assignment(
    request: Request,
    assignment_id: int,
    file: UploadFile = File(...)
):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=403)

    # Сохраняем файл
    safe_filename = f"{user.id}_{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = UPLOAD_DIR / safe_filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Создаём сабмишен
    db = SessionLocal()
    submission = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        file_path=str(filepath),
        status="pending"
    )
    db.add(submission)
    db.commit()
    db.close()

    return """
    <div class="alert alert-info alert-dismissible fade show d-flex align-items-center" role="alert">
      <i class="bi bi-hourglass-split fs-4 me-3"></i>
      <div>
        <strong>Работа отправлена на проверку!</strong><br>
        <small>Преподаватель получит уведомление.</small>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    """

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
    
    # Курс
    course = Course(
        title="Введение в машинное обучение",
        description="Курс для начинающих",
        tags="ml,python"
    )
    db.add(course)
    db.commit()
    
    # Задания
    assignments = [
        Assignment(course_id=course.id, title="ДЗ 1: Линейная регрессия", description="Реализуйте на Python"),
        Assignment(course_id=course.id, title="ДЗ 2: Классификация", description="scikit-learn"),
    ]
    db.add_all(assignments)
    db.commit()
    
    # Сабмишены
    sub = Submission(
        assignment_id=assignments[0].id,
        student_id=student.id,
        file_path="uploads/demo.pdf",
        status="pending"
    )
    db.add(sub)
    db.commit()
    db.close()
    
    return "<h2>✅ Демо-данные созданы</h2><p><a href='/'>Вернуться</a></p>"