# src/ml_recommender.py
from typing import List, Dict
from models import User

class SimpleRecommender:
    """
    Простая, но расширяемая рекомендательная система.
    
    Для MVP — правила на основе тегов.
    Позже можно заменить на:
    - sklearn (TF-IDF + cosine similarity)
    - surprise (коллаборативная фильтрация)
    - нейросеть (PyTorch)
    """
    
    # База знаний: курс → теги
    COURSE_TAGS = {
        1: ["ml", "python", "math"],
        2: ["nlp", "ml", "transformers"],
        3: ["cv", "ml", "pytorch"],
        4: ["ds", "sql", "pandas"],
    }
    
    # Описание курсов (в реальном проекте — из БД)
    COURSES = {
        1: {"title": "Введение в машинное обучение", "description": "Линейная регрессия, классификация, scikit-learn"},
        2: {"title": "NLP с нуля", "description": "BERT, токенизация, классификация текста"},
        3: {"title": "Компьютерное зрение", "description": "CNN, OpenCV, YOLO"},
        4: {"title": "Анализ данных", "description": "Pandas, визуализация, SQL"},
    }

    def recommend_for_user(self, completed_course_ids: List[int]) -> List[Dict]:
        """
        Возвращает рекомендации на основе пройденных курсов.
        
        Логика:
        - Если пройден курс 1 (ML) → рекомендуем 2 (NLP) и 3 (CV)
        - Если ничего не пройдено → курс 1
        """
        if not completed_course_ids:
            return [{
                "id": 1,
                "title": self.COURSES[1]["title"],
                "reason": "Стартовый курс для всех",
                "tags": self.COURSE_TAGS[1]
            }]

        # Проверяем: прошёл ли ML?
        has_ml = any(cid in [1] for cid in completed_course_ids)
        if has_ml:
            return [
                {
                    "id": 2,
                    "title": self.COURSES[2]["title"],
                    "reason": "Вы освоили ML — пора в NLP!",
                    "tags": self.COURSE_TAGS[2]
                },
                {
                    "id": 3,
                    "title": self.COURSES[3]["title"],
                    "reason": "Компьютерное зрение — логичное продолжение ML",
                    "tags": self.COURSE_TAGS[3]
                }
            ]

        return [{
            "id": 4,
            "title": self.COURSES[4]["title"],
            "reason": "Попробуйте анализ данных — это весело!",
            "tags": self.COURSE_TAGS[4]
        }]