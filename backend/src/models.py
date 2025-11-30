# src/models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)  # "student" или "teacher"

    # Связь: один пользователь → много сабмишенов
    submissions = relationship("Submission", back_populates="student")
    # Связь: один пользователь → много записей на курсы
    enrollments = relationship("Enrollment", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    tags = Column(String)  # "ml,python,math" — для ML
    # Новое поле: контент курса (опционально, если весь контент в модулях)
    content = Column(Text, nullable=True)
    author = Column(String) # Поле для автора

    # Связь: один курс → много модулей
    modules = relationship("Module", back_populates="course", order_by="Module.order")
    # Связь: один курс → много записей на курс
    enrollments = relationship("Enrollment", back_populates="course")


class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False) # "text", "assignment", "video"
    content = Column(Text, nullable=True) # HTML-контент для текста
    order = Column(Integer, default=0) # Порядок модуля в курсе

    # Связь: модуль → курс
    course = relationship("Course", back_populates="modules")
    # Связь: модуль → задание (если type == "assignment")
    assignment = relationship("Assignment", back_populates="module", uselist=False, cascade="all, delete-orphan")
    # Связь: модуль → видео (если type == "video")
    video = relationship("Video", back_populates="module", uselist=False, cascade="all, delete-orphan")


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    # Поле дедлайна
    deadline = Column(DateTime, nullable=True)
    # Поле для данных теста (вопросы, варианты, правильные ответы) - JSON
    test_data = Column(Text, nullable=True) # JSON-строка

    # Связь: задание → модуль
    module = relationship("Module", back_populates="assignment")
    # Связь: задание → много сабмишенов
    submissions = relationship("Submission", back_populates="assignment")


class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    # Путь или ID видео (внешнее или локальное)
    video_url = Column(String, nullable=True)
    # Тип видео: 'youtube', 'rutube', 'embedded_mp4', 'placeholder' и т.д.
    video_type = Column(String, default="placeholder")

    # Связь: видео -> модуль
    module = relationship("Module", back_populates="video")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String, nullable=True) # Может быть NULL для тестов
    status = Column(String, default="pending")  # pending → reviewed (для теста: submitted -> reviewed/graded)
    feedback = Column(Text, nullable=True)
    grade = Column(Integer, nullable=True) # Оценка за тест (например, 0-100%)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    # Поле для ответов студента на тест (JSON)
    test_answers = Column(Text, nullable=True) # JSON-строка

    # Связи:
    student = relationship("User", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")


class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    role = Column(String, nullable=False) # "student", "teacher"

    # Связи:
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")