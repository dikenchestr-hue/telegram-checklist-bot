# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

class Keyboards:
    """Класс для хранения всех клавиатур (создаются один раз)"""
    
    # Клавиатура для ответов Да/Нет
    yes_no = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Клавиатура для старта
    start = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚀 Старт")]],
        resize_keyboard=True
    )
    
    # Клавиатура для выбора типа статьи
    article_type = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔬 Оригинальная статья")],
            [KeyboardButton(text="📚 Обзорная статья")]
        ],
        resize_keyboard=True
    )
    
    # Клавиатура для выбора дисциплины
    discipline = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📖 Гуманитарные науки")],
            [KeyboardButton(text="🔬 Естественные и технические науки")],
            [KeyboardButton(text="🏥 Медицинские науки")],
            [KeyboardButton(text="📚 Педагогические науки")],
            [KeyboardButton(text="📊 Социальные науки")]
        ],
        resize_keyboard=True
    )
    
    # Клавиатура удаления
    remove = ReplyKeyboardRemove()

# Создаем экземпляр для импорта
keyboards = Keyboards()
