from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
import time
from ..utils.logger import logger

class CacheManager:
    def __init__(self, default_duration: int = 300):
        self.default_duration = default_duration
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._expiry: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                if key in self._expiry and time.time() > self._expiry[key]:
                    del self._cache[key]
                    del self._expiry[key]
                    return None
                return self._cache[key].copy()
            return None

    def set(self, key: str, value: Any, duration: Optional[int] = None):
        with self._lock:
            self._cache[key] = value
            duration = duration or self.default_duration
            self._expiry[key] = time.time() + duration

    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._expiry.clear()

    def has(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                if key in self._expiry and time.time() > self._expiry[key]:
                    del self._cache[key]
                    del self._expiry[key]
                    return False
                return True
            return False

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self):
        with self._lock:
            current_time = time.time()
            expired_keys = [k for k, exp_time in self._expiry.items() 
                          if current_time > exp_time]
            for key in expired_keys:
                del self._cache[key]
                del self._expiry[key]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for k in self._expiry if time.time() > self._expiry[k])
            return {
                'total_entries': total,
                'expired_entries': expired,
                'active_entries': total - expired
            }

cache_manager = CacheManager()
