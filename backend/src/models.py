# src/models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)  # "student" или "teacher"

    # Связь: один пользователь → много сабмишенов
    submissions = relationship("Submission", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    tags = Column(String)  # "ml,python,math" — для ML
    # Новое поле: контент курса
    content = Column(Text, nullable=True)

    # Связь: один курс → много заданий
    assignments = relationship("Assignment", back_populates="course")


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String)
    description = Column(Text)

    # Связь: задание → курс
    course = relationship("Course", back_populates="assignments")

    # Связь: задание → много сабмишенов (опционально, но полезно)
    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    file_path = Column(String)
    status = Column(String, default="pending")  # pending → reviewed
    feedback = Column(Text, nullable=True)
    grade = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Связи:
    student = relationship("User", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String)
    content_type = Column(String)  # "text", "video", "pdf"
    content_url = Column(String)   # YouTube URL / путь к PDF
    text_content = Column(Text, nullable=True)  # для текста
    order = Column(Integer, default=0)