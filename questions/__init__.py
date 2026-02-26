# questions/__init__.py
from .review import REVIEW_QUESTIONS
from .natural import NATURAL_QUESTIONS
from .medical import MEDICAL_QUESTIONS
from .pedagog import PEDAGOGICAL_QUESTIONS
from .social import SOCIAL_QUESTIONS
from .humanities import HUMANITIES_QUESTIONS

# Словарь для быстрого доступа ко всем вопросам
QUESTIONS_MAP = {
    'review': REVIEW_QUESTIONS,
    'natural': NATURAL_QUESTIONS,
    'medical': MEDICAL_QUESTIONS,
    'pedagog': PEDAGOGICAL_QUESTIONS,
    'social': SOCIAL_QUESTIONS,
    'humanities': HUMANITIES_QUESTIONS
}

# Названия дисциплин
DISCIPLINE_NAMES = {
    'review': "ОБЗОРНАЯ СТАТЬЯ",
    'natural': "ЕСТЕСТВЕННЫЕ И ТЕХНИЧЕСКИЕ НАУКИ",
    'medical': "МЕДИЦИНСКИЕ НАУКИ",
    'pedagog': "ПЕДАГОГИЧЕСКИЕ НАУКИ",
    'social': "СОЦИАЛЬНЫЕ НАУКИ",
    'humanities': "ГУМАНИТАРНЫЕ НАУКИ"
}

# Соответствие кнопок и кодов дисциплин
DISCIPLINE_BUTTON_MAP = {
    "📖 Гуманитарные науки": 'humanities',
    "🔬 Естественные и технические науки": 'natural',
    "🏥 Медицинские науки": 'medical',
    "📚 Педагогические науки": 'pedagog',
    "📊 Социальные науки": 'social'
}

__all__ = [
    'QUESTIONS_MAP',
    'DISCIPLINE_NAMES',
    'DISCIPLINE_BUTTON_MAP',
    'REVIEW_QUESTIONS',
    'NATURAL_QUESTIONS',
    'MEDICAL_QUESTIONS',
    'PEDAGOGICAL_QUESTIONS',
    'SOCIAL_QUESTIONS',
    'HUMANITIES_QUESTIONS'
]
