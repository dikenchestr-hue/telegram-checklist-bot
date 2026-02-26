# database.py
import json
import time
from typing import Dict, Any, Optional
from collections import defaultdict
import asyncio
from datetime import datetime

class UserDataManager:
    """Менеджер данных пользователя с автоматической очисткой и кэшированием"""
    
    def __init__(self, timeout: int = 3600):
        self._data: Dict[int, Dict[str, Any]] = {}
        self._timeout = timeout
        self._last_access: Dict[int, float] = {}
        self._lock = asyncio.Lock()
        
    async def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя"""
        async with self._lock:
            if user_id in self._data:
                self._last_access[user_id] = time.time()
                # Возвращаем копию, чтобы избежать изменений
                return self._data[user_id].copy()
            return None
    
    async def set(self, user_id: int, data: Dict[str, Any]):
        """Сохранить данные пользователя"""
        async with self._lock:
            self._data[user_id] = data.copy()
            self._last_access[user_id] = time.time()
            # Запускаем очистку в фоне
            asyncio.create_task(self._cleanup())
    
    async def update(self, user_id: int, **kwargs):
        """Обновить данные пользователя"""
        async with self._lock:
            if user_id in self._data:
                self._data[user_id].update(kwargs)
                self._last_access[user_id] = time.time()
    
    async def delete(self, user_id: int):
        """Удалить данные пользователя"""
        async with self._lock:
            self._data.pop(user_id, None)
            self._last_access.pop(user_id, None)
    
    async def _cleanup(self):
        """Очистка старых данных"""
        await asyncio.sleep(60)  # Проверка раз в минуту
        async with self._lock:
            now = time.time()
            to_delete = [
                uid for uid, last in self._last_access.items()
                if now - last > self._timeout
            ]
            for uid in to_delete:
                self._data.pop(uid, None)
                self._last_access.pop(uid, None)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        async with self._lock:
            return {
                'active_users': len(self._data),
                'oldest_access': min(self._last_access.values()) if self._last_access else None,
                'newest_access': max(self._last_access.values()) if self._last_access else None
            }

# Создаем глобальный экземпляр
user_manager = UserDataManager()
