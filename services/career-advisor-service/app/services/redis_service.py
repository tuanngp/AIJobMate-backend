import json
import logging
from typing import Any, Optional
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'RedisService':
        """
        Get Redis singleton instance
        """
        if cls._instance is None:
            cls._instance = RedisService()
        return cls._instance
    
    def __init__(self):
        """
        Initialize Redis connection pool
        """
        if not hasattr(self, 'redis_client'):
            logger.info(f"Khởi tạo Redis connection pool - Host: {settings.REDIS_HOST}, Port: {settings.REDIS_PORT}")
            try:
                self.pool = ConnectionPool(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True
                )
                self.redis_client = Redis(connection_pool=self.pool)
                logger.info("Redis connection pool được khởi tạo thành công")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Redis connection: {str(e)}", exc_info=True)
                raise
            logger.info("Redis connection pool initialized")
        
    async def set_cache(self, key: str, value: Any, expiry: int = 3600) -> bool:
        """
        Lưu giá trị vào cache với thời gian hết hạn.
        
        Args:
            key: Cache key
            value: Giá trị cần cache
            expiry: Thời gian hết hạn (giây)
        """
        try:
            logger.debug(f"Đang lưu cache với key: {key}, expiry: {expiry}s")
            json_value = json.dumps(value)
            result = await self.redis_client.setex(key, expiry, json_value)
            if result:
                logger.info(f"Đã lưu cache thành công với key: {key}")
            else:
                logger.warning(f"Không thể lưu cache với key: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Lỗi khi cache key {key}: {str(e)}", exc_info=True)
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Lấy giá trị từ cache.
        
        Args:
            key: Cache key
        """
        try:
            logger.debug(f"Đang lấy cache với key: {key}")
            value = await self.redis_client.get(key)
            if value:
                logger.info(f"Đã tìm thấy cache cho key: {key}")
                return json.loads(value)
            logger.info(f"Không tìm thấy cache cho key: {key}")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy cache key {key}: {str(e)}", exc_info=True)
            return None

    async def delete_cache(self, key: str) -> bool:
        """
        Xóa giá trị khỏi cache.
        
        Args:
            key: Cache key
        """
        try:
            return bool(await self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Lỗi khi xóa cache: {str(e)}")
            return False

    def generate_cache_key(self, prefix: str, *args) -> str:
        """
        Tạo cache key từ prefix và các tham số.
        """
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

    def close(self):
        """
        Đóng kết nối Redis khi shutdown
        """
        if hasattr(self, 'redis_client'):
            self.redis_client.aclose()
            self.pool.aclose()
            logger.info("Redis connection closed")