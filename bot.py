import logging
import asyncio
import os
import time
from functools import lru_cache
from typing import Dict, Any, Optional
import threading
from flask import Flask

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Импортируем вопросы из модуля
from questions import (
    REVIEW_QUESTIONS, NATURAL_QUESTIONS, MEDICAL_QUESTIONS,
    PEDAGOGICAL_QUESTIONS, SOCIAL_QUESTIONS, HUMANITIES_QUESTIONS,
    SECTION_NAMES, DISCIPLINE_NAMES, QUESTION_COUNTS
)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ Не задан BOT_TOKEN в переменных окружения!")

# Настройка логирования
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Создаем экземпляры бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== КОНСТАНТЫ =====
# Словарь для быстрого доступа ко всем вопросам
QUESTIONS_MAP = {
    'review': REVIEW_QUESTIONS,
    'natural': NATURAL_QUESTIONS,
    'medical': MEDICAL_QUESTIONS,
    'pedagog': PEDAGOGICAL_QUESTIONS,
    'social': SOCIAL_QUESTIONS,
    'humanities': HUMANITIES_QUESTIONS
}

# Карта соответствия текста кнопок и кодов дисциплин
DISCIPLINE_MAP = {
    "📖 Гуманитарные": 'humanities',
    "🔬 Естественные": 'natural',
    "🏥 Медицинские": 'medical',
    "📚 Педагогические": 'pedagog',
    "📊 Социальные": 'social'
}

# ===== ОПТИМИЗИРОВАННЫЕ СОСТОЯНИЯ =====
class ChecklistStates(StatesGroup):
    choosing_article_type = State()
    choosing_discipline = State()
    answering = State()  # Единое состояние для ответов

# ===== МЕНЕДЖЕР ДАННЫХ ПОЛЬЗОВАТЕЛЯ =====
class UserDataManager:
    def __init__(self, timeout=3600):
        self._data: Dict[int, Dict[str, Any]] = {}
        self._timeout = timeout
        self._last_access: Dict[int, float] = {}
    
    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя"""
        if user_id in self._data:
            self._last_access[user_id] = time.time()
            return self._data[user_id]
        return None
    
    def set(self, user_id: int, data: Dict[str, Any]):
        """Сохранить данные пользователя"""
        self._data[user_id] = data
        self._last_access[user_id] = time.time()
        self._cleanup()
    
    def delete(self, user_id: int):
        """Удалить данные пользователя"""
        self._data.pop(user_id, None)
        self._last_access.pop(user_id, None)
    
    def _cleanup(self):
        """Очистка старых данных"""
        now = time.time()
        to_delete = [
            uid for uid, last in self._last_access.items()
            if now - last > self._timeout
        ]
        for uid in to_delete:
            self.delete(uid)

user_manager = UserDataManager()

# ===== КЭШИРОВАНИЕ =====
@lru_cache(maxsize=32)
def get_questions(category: str) -> list:
    """Получить вопросы для категории"""
    return QUESTIONS_MAP.get(category, [])

@lru_cache(maxsize=32)
def get_question_count(category: str) -> int:
    """Получить количество вопросов"""
    return QUESTION_COUNTS.get(category, 0)

@lru_cache(maxsize=32)
def get_section_name(category: str, question_num: int) -> str:
    """Получить название раздела для результата"""
    sections = SECTION_NAMES.get(category, {})
    return sections.get(question_num, f"Вопрос {question_num}")

# ===== ПРЕДЗАГРУЖЕННЫЕ КЛАВИАТУРЫ =====
YES_NO_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]],
    resize_keyboard=True
)

START_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚀 Старт")]],
    resize_keyboard=True
)

ARTICLE_TYPE_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔬 Оригинальная")],
        [KeyboardButton(text="📚 Обзорная")]
    ],
    resize_keyboard=True
)

DISCIPLINE_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Гуманитарные")],
        [KeyboardButton(text="🔬 Естественные")],
        [KeyboardButton(text="🏥 Медицинские")],
        [KeyboardButton(text="📚 Педагогические")],
        [KeyboardButton(text="📊 Социальные")]
    ],
    resize_keyboard=True
)

# ===== FLASK ДЛЯ RENDER =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот для проверки научных статей работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)

threading.Thread(target=run_flask, daemon=True).start()

# ===== ОЧИСТКА ПРЕДЫДУЩИХ СЕССИЙ =====
async def cleanup_previous():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Предыдущие сессии очищены")

asyncio.run(cleanup_previous())

# ===== КОМАНДА /start =====
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "📋 **Чек-лист для научных статей**\n\n"
        "Помогу проверить статью перед подачей в журнал.\n\n"
        "**Нажмите Старт для начала** 👇",
        reply_markup=START_KEYBOARD,
        parse_mode="Markdown"
    )

# ===== ОБРАБОТКА СТАРТ =====
@dp.message(lambda m: m.text == "🚀 Старт")
async def process_start(message: types.Message, state: FSMContext):
    await message.answer(
        "**Выберите тип статьи:**",
        reply_markup=ARTICLE_TYPE_KEYBOARD,
        parse_mode="Markdown"
    )
    await state.set_state(ChecklistStates.choosing_article_type)

# ===== ВЫБОР ТИПА СТАТЬИ =====
@dp.message(ChecklistStates.choosing_article_type)
async def process_article_type(message: types.Message, state: FSMContext):
    if message.text == "📚 Обзорная":
        category = 'review'
        await start_questionnaire(message, state, category)
        
    elif message.text == "🔬 Оригинальная":
        await message.answer(
            "**Выберите дисциплину:**",
            reply_markup=DISCIPLINE_KEYBOARD,
            parse_mode="Markdown"
        )
        await state.set_state(ChecklistStates.choosing_discipline)
    else:
        await message.answer("Пожалуйста, используйте кнопки ниже")

# ===== ВЫБОР ДИСЦИПЛИНЫ =====
@dp.message(ChecklistStates.choosing_discipline)
async def process_discipline(message: types.Message, state: FSMContext):
    category = DISCIPLINE_MAP.get(message.text)
    if not category:
        await message.answer("Пожалуйста, выберите дисциплину из списка")
        return
    
    await start_questionnaire(message, state, category)

# ===== НАЧАЛО ОПРОСА =====
async def start_questionnaire(message: types.Message, state: FSMContext, category: str):
    """Общая функция начала опроса"""
    user_id = message.from_user.id
    
    # Сохраняем данные пользователя
    user_manager.set(user_id, {
        'category': category,
        'answers': {},
        'current': 1
    })
    
    # Сохраняем состояние
    await state.update_data(category=category, current=1)
    await state.set_state(ChecklistStates.answering)
    
    # Отправляем первый вопрос
    questions = get_questions(category)
    await message.answer(
        questions[0],
        reply_markup=YES_NO_KEYBOARD,
        parse_mode="Markdown"
    )

# ===== ОБРАБОТКА ОТВЕТОВ =====
@dp.message(ChecklistStates.answering)
async def handle_answer(message: types.Message, state: FSMContext):
    # Проверка ответа
    if message.text not in ["✅ Да", "❌ Нет"]:
        await message.answer(
            "Пожалуйста, используйте кнопки Да или Нет",
            reply_markup=YES_NO_KEYBOARD
        )
        return
    
    user_id = message.from_user.id
    user_data = user_manager.get(user_id)
    
    if not user_data:
        await message.answer("❌ Ошибка. Начните заново с /start")
        await state.clear()
        return
    
    # Получаем текущее состояние
    category = user_data['category']
    current = user_data['current']
    questions = get_questions(category)
    total = get_question_count(category)
    
    # Сохраняем ответ
    answer = "да" if message.text == "✅ Да" else "нет"
    user_data['answers'][f"q{current}"] = answer
    
    # Проверяем, есть ли следующий вопрос
    if current < total:
        # Переходим к следующему вопросу
        next_q = current + 1
        user_data['current'] = next_q
        
        # Показываем прогресс (каждые 5 вопросов или на последних)
        if next_q % 5 == 0 or next_q == total:
            progress = "▓" * next_q + "░" * (total - next_q)
            await message.answer(f"📊 Прогресс: {next_q}/{total}\n{progress}")
        
        await message.answer(
            questions[next_q - 1],
            reply_markup=YES_NO_KEYBOARD,
            parse_mode="Markdown"
        )
    else:
        # Вопросы закончились - показываем результаты
        await show_results(message, user_data)
        await state.clear()
        user_manager.delete(user_id)

# ===== ПОКАЗ РЕЗУЛЬТАТОВ =====
async def show_results(message: types.Message, user_data: dict):
    answers = user_data['answers']
    category = user_data['category']
    total = get_question_count(category)
    
    answered_no = sum(1 for v in answers.values() if v == "нет")
    answered_yes = total - answered_no
    
    # Прогресс-бар
    progress = "█" * answered_yes + "░" * answered_no
    
    # Заголовок
    title = f"📋 **ЧЕК-ЛИСТ: {DISCIPLINE_NAMES.get(category, 'СТАТЬЯ')}**"
    
    result = f"{title}\n\n"
    result += f"**Прогресс:** {progress}\n"
    result += f"✅ **Выполнено:** {answered_yes}/{total}\n"
    result += f"⚠️ **Требуют внимания:** {answered_no}\n\n"
    
    if answered_no > 0:
        result += "**🔴 ЧТО НУЖНО ПРОВЕРИТЬ:**\n"
        
        for i in range(1, total + 1):
            if answers.get(f'q{i}') == "нет":
                section_name = get_section_name(category, i)
                result += f"• {section_name}\n"
    else:
        result += "🎉 **ОТЛИЧНО! Все пункты выполнены!**\n"
        result += "Можно отправлять статью в журнал! 📤"
    
    await message.answer(result, parse_mode="Markdown")
    
    # Финальное сообщение
    await message.answer(
        "✨ Для нового опроса отправьте /start",
        reply_markup=ReplyKeyboardRemove()
    )

# ===== КОМАНДА /cancel =====
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    user_manager.delete(message.from_user.id)
    await state.clear()
    await message.answer(
        "❌ Опрос отменен. Для начала отправьте /start",
        reply_markup=ReplyKeyboardRemove()
    )

# ===== ЗАПУСК БОТА =====
async def main():
    print("🚀 Бот запускается...")
    print(f"📊 Загружено дисциплин: {len(QUESTIONS_MAP)}")
    for cat, qs in QUESTIONS_MAP.items():
        print(f"  • {cat}: {len(qs)} вопросов")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
