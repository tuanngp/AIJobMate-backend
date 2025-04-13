import json
import logging
from typing import Any, Optional
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'RedisService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
    def set_cache(self, key: str, value: Any, expiry: int = 3600) -> bool:
        """
        Lưu giá trị vào cache với thời gian hết hạn.
        
        Args:
            key: Cache key
            value: Giá trị cần cache
            expiry: Thời gian hết hạn (giây)
        """
        try:
            json_value = json.dumps(value)
            return self.redis_client.setex(key, expiry, json_value)
        except Exception as e:
            logger.error(f"Lỗi khi cache: {str(e)}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """
        Lấy giá trị từ cache.
        
        Args:
            key: Cache key
        """
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy cache: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """
        Xóa giá trị khỏi cache.
        
        Args:
            key: Cache key
        """
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Lỗi khi xóa cache: {str(e)}")
            return False

    def generate_cache_key(self, prefix: str, *args) -> str:
        """
        Tạo cache key từ prefix và các tham số.
        """
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"