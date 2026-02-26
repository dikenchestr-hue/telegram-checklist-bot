# bot.py
import asyncio
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from flask import Flask
import threading

from config import config
from keyboards import keyboards
from database import user_manager
from questions import QUESTIONS_MAP, DISCIPLINE_NAMES, DISCIPLINE_BUTTON_MAP

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание экземпляров бота
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== Flask сервер для Render =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот для проверки научных статей работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=config.PORT, debug=False)

threading.Thread(target=run_flask, daemon=True).start()

# ===== Состояния =====
class ChecklistStates(StatesGroup):
    choosing_article_type = State()
    choosing_discipline = State()
    answering = State()

# ===== Декоратор для замера времени =====
def timing_decorator(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        if elapsed_time > 0.5:
            logger.warning(f"⚠️ {func.__name__} выполнился за {elapsed_time:.2f} секунд")
        return result
    return wrapper

# ===== Команда /start =====
@dp.message(CommandStart())
@timing_decorator
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    await message.answer(
        "📋 **Добро пожаловать в чек-лист подготовки научной статьи!**\n\n"
        "Этот бот поможет авторам проверить, все ли требования выполнены "
        "перед подачей статьи в журнал.\n\n"
        "✅ Вам будет предложено ответить на серию вопросов по структуре и "
        "содержанию вашей статьи. Отвечайте, используя кнопки **Да** или **Нет**.\n\n"
        "По окончании вы получите список пунктов, которые требуют доработки.\n\n"
        "**Для начала работы нажмите кнопку Старт ниже** 👇",
        reply_markup=keyboards.start,
        parse_mode="Markdown"
    )

# ===== Обработка кнопки Старт =====
@dp.message(lambda message: message.text == "🚀 Старт")
@timing_decorator
async def process_start(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки Старт"""
    await message.answer(
        "**Выберите тип вашей статьи:**",
        reply_markup=keyboards.article_type,
        parse_mode="Markdown"
    )
    await state.set_state(ChecklistStates.choosing_article_type)

# ===== Выбор типа статьи =====
@dp.message(ChecklistStates.choosing_article_type)
@timing_decorator
async def process_article_type(message: types.Message, state: FSMContext):
    """Обработка выбора типа статьи"""
    article_type = message.text
    
    if article_type == "📚 Обзорная статья":
        await start_questionnaire(message, state, 'review')
    elif article_type == "🔬 Оригинальная статья":
        await message.answer(
            "**Выберите научную дисциплину:**",
            reply_markup=keyboards.discipline,
            parse_mode="Markdown"
        )
        await state.set_state(ChecklistStates.choosing_discipline)
    else:
        await message.answer(
            "Пожалуйста, выберите тип статьи, используя кнопки ниже"
        )

# ===== Выбор дисциплины =====
@dp.message(ChecklistStates.choosing_discipline)
@timing_decorator
async def process_discipline(message: types.Message, state: FSMContext):
    """Обработка выбора дисциплины"""
    category = DISCIPLINE_BUTTON_MAP.get(message.text)
    
    if not category:
        await message.answer(
            "Пожалуйста, выберите дисциплину, используя кнопки ниже"
        )
        return
    
    await start_questionnaire(message, state, category)

# ===== Начало опроса =====
async def start_questionnaire(message: types.Message, state: FSMContext, category: str):
    """Общая функция начала опроса"""
    user_id = message.from_user.id
    questions = QUESTIONS_MAP.get(category, [])
    
    if not questions:
        logger.error(f"❌ Вопросы для категории {category} не найдены")
        await message.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=keyboards.remove
        )
        await state.clear()
        return
    
    # Сохраняем данные пользователя
    await user_manager.set(user_id, {
        'category': category,
        'answers': {},
        'current_question': 1,
        'total_questions': len(questions),
        'start_time': datetime.now().isoformat()
    })
    
    # Сохраняем состояние
    await state.update_data(category=category)
    await state.set_state(ChecklistStates.answering)
    
    # Отправляем первый вопрос
    await message.answer(
        questions[0],
        reply_markup=keyboards.yes_no,
        parse_mode="Markdown"
    )

# ===== Обработка ответов =====
@dp.message(ChecklistStates.answering)
@timing_decorator
async def handle_answer(message: types.Message, state: FSMContext):
    """Обработка ответов на вопросы"""
    # Проверка корректности ответа
    if message.text not in ["✅ Да", "❌ Нет"]:
        await message.answer(
            "Пожалуйста, используйте кнопки **✅ Да** или **❌ Нет**",
            reply_markup=keyboards.yes_no,
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    user_data = await user_manager.get(user_id)
    
    if not user_data:
        logger.error(f"❌ Данные пользователя {user_id} не найдены")
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, начните заново с команды /start",
            reply_markup=keyboards.remove
        )
        await state.clear()
        return
    
    # Получаем данные
    category = user_data['category']
    current = user_data['current_question']
    questions = QUESTIONS_MAP.get(category, [])
    total = user_data['total_questions']
    
    # Сохраняем ответ
    answer = "да" if message.text == "✅ Да" else "нет"
    user_data['answers'][f"q{current}"] = answer
    
    # Проверяем, есть ли следующий вопрос
    if current < total:
        # Переходим к следующему вопросу
        next_question = current + 1
        await user_manager.update(user_id, current_question=next_question)
        
        # Показываем прогресс (каждые 5 вопросов или на последних)
        if next_question % 5 == 0 or next_question == total:
            progress = "▓" * next_question + "░" * (total - next_question)
            await message.answer(
                f"📊 **Прогресс:** {next_question}/{total}\n"
                f"```\n{progress}\n```",
                parse_mode="Markdown"
            )
        
        # Отправляем следующий вопрос
        await message.answer(
            questions[next_question - 1],
            reply_markup=keyboards.yes_no,
            parse_mode="Markdown"
        )
    else:
        # Вопросы закончились - показываем результаты
        await show_results(message, user_data)
        await state.clear()
        await user_manager.delete(user_id)

# ===== Показ результатов =====
async def show_results(message: types.Message, user_data: dict):
    """Отображение результатов опроса"""
    answers = user_data['answers']
    category = user_data['category']
    total = user_data['total_questions']
    
    # Подсчет ответов
    answered_no = sum(1 for value in answers.values() if value == "нет")
    answered_yes = total - answered_no
    
    # Создание прогресс-бара
    progress = "█" * answered_yes + "░" * answered_no
    
    # Заголовок
    title = f"📋 **ЧЕК-ЛИСТ: {DISCIPLINE_NAMES.get(category, 'СТАТЬЯ')}**"
    
    result = f"{title}\n\n"
    result += f"**Прогресс:** {progress}\n"
    result += f"✅ **Выполнено:** {answered_yes}/{total}\n"
    result += f"⚠️ **Требуют внимания:** {answered_no}\n\n"
    
    if answered_no > 0:
        result += "**🔴 ЧТО НУЖНО ПРОВЕРИТЬ:**\n"
        
        # Получаем вопросы для формирования списка
        questions = QUESTIONS_MAP.get(category, [])
        
        for i in range(1, total + 1):
            if answers.get(f'q{i}') == "нет":
                # Извлекаем суть вопроса (первую строку после заголовка)
                question_text = questions[i - 1]
                lines = question_text.split('\n')
                
                # Пытаемся найти содержательную часть
                meaningful_part = ""
                for line in lines:
                    if line and not line.startswith('**') and not line.startswith('📄') and not line.startswith('🔤') and not line.startswith('📌') and not line.startswith('📚') and not line.startswith('🧪') and not line.startswith('📊') and not line.startswith('💬') and not line.startswith('🎯') and not line.startswith('📖') and not line.startswith('📜'):
                        meaningful_part = line
                        break
                
                if not meaningful_part and len(lines) > 1:
                    meaningful_part = lines[-1]  # Берем последнюю строку
                
                if len(meaningful_part) > 100:
                    meaningful_part = meaningful_part[:100] + "..."
                
                result += f"• {meaningful_part}\n"
    else:
        result += "🎉 **ОТЛИЧНО! Все пункты выполнены!**\n"
        result += "Можно отправлять статью в журнал! 📤"
    
    await message.answer(result, parse_mode="Markdown")
    
    # Финальное сообщение
    await message.answer(
        "✨ **Чек-лист завершен!**\n\nЧтобы начать заново, отправьте /start",
        reply_markup=keyboards.remove,
        parse_mode="Markdown"
    )

# ===== Команда /cancel =====
@dp.message(Command(commands=["cancel"]))
@timing_decorator
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего опроса"""
    user_id = message.from_user.id
    await user_manager.delete(user_id)
    await state.clear()
    
    await message.answer(
        "❌ Опрос отменен. Чтобы начать заново, отправьте /start",
        reply_markup=keyboards.remove
    )

# ===== Команда /stats (для администратора) =====
@dp.message(Command(commands=["stats"]))
@timing_decorator
async def cmd_stats(message: types.Message, state: FSMContext):
    """Статистика работы бота"""
    stats = await user_manager.get_stats()
    
    stats_text = (
        "📊 **Статистика бота**\n\n"
        f"👥 Активных пользователей: {stats['active_users']}\n"
        f"⏱️ Время работы: {time.time() - bot.start_time:.0f} секунд"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")

# ===== Обработка всех остальных сообщений =====
@dp.message()
@timing_decorator
async def handle_unknown(message: types.Message, state: FSMContext):
    """Обработка неизвестных команд"""
    await message.answer(
        "Я вас не понимаю. Пожалуйста, используйте кнопки или команду /start",
        reply_markup=keyboards.start
    )

# ===== Запуск бота =====
async def on_startup():
    """Действия при запуске бота"""
    logger.info("🚀 Бот запускается...")
    
    # Очистка предыдущих сессий
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Предыдущие сессии очищены")
    
    # Сохраняем время запуска для статистики
    bot.start_time = time.time()
    
    # Вывод информации о загруженных вопросах
    for category, questions in QUESTIONS_MAP.items():
        logger.info(f"  • {category}: {len(questions)} вопросов")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🛑 Бот останавливается...")
    await bot.session.close()

async def main():
    """Главная функция"""
    await on_startup()
    
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
