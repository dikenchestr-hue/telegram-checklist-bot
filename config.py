# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не задан в переменных окружения!")
    
    # Redis для кэширования
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Настройки
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'ERROR')
    
    # Таймауты
    USER_DATA_TIMEOUT = 3600  # 1 час
    CACHE_TTL = 300  # 5 минут
    
    # Порты
    PORT = int(os.getenv('PORT', 10000))

config = Config()
