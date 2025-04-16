import json
import logging
import asyncio
from typing import Any, Optional
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None
    _pool = None
    _initialized = False

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
        if RedisService._instance is not None and self is not RedisService._instance:
            raise RuntimeError("RedisService is a singleton. Use get_instance() instead")
        
        if not RedisService._initialized:
            self._initialize_connection()
            RedisService._initialized = True
    
    def _initialize_connection(self):
        """
        Khởi tạo Redis connection
        """
        try:
            if RedisService._pool is None:
                RedisService._pool = ConnectionPool(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    health_check_interval=30
                )
            self.redis_client = Redis(connection_pool=RedisService._pool)
            logger.info("Redis connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing Redis connection: {str(e)}", exc_info=True)
            raise
        
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
            result = await asyncio.wait_for(
                self.redis_client.setex(key, expiry, json_value),
                timeout=5.0
            )
            if result:
                logger.info(f"Đã lưu cache thành công với key: {key}")
            else:
                logger.warning(f"Không thể lưu cache với key: {key}")
            return bool(result)
        except asyncio.TimeoutError:
            logger.error(f"Timeout khi cache key {key}")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi cache key {key}: {str(e)}", exc_info=True)
            await self._reconnect_if_needed()
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Lấy giá trị từ cache.
        
        Args:
            key: Cache key
        """
        try:
            logger.debug(f"Đang lấy cache với key: {key}")
            value = await asyncio.wait_for(
                self.redis_client.get(key),
                timeout=5.0
            )
            if value:
                logger.info(f"Đã tìm thấy cache cho key: {key}")
                return json.loads(value)
            logger.info(f"Không tìm thấy cache cho key: {key}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout khi lấy cache key {key}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi JSON khi giải mã cache cho key {key}: {str(e)}")
            await self.delete_cache(key)
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy cache key {key}: {str(e)}", exc_info=True)
            await self._reconnect_if_needed()
            return None

    async def delete_cache(self, key: str) -> bool:
        """
        Xóa giá trị khỏi cache.
        
        Args:
            key: Cache key
        """
        try:
            return bool(await asyncio.wait_for(
                self.redis_client.delete(key),
                timeout=5.0
            ))
        except asyncio.TimeoutError:
            logger.error(f"Timeout khi xóa cache key {key}")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xóa cache: {str(e)}")
            await self._reconnect_if_needed()
            return False

    async def _reconnect_if_needed(self):
        """
        Thử kết nối lại nếu kết nối hiện tại có vấn đề
        """
        try:
            # Kiểm tra kết nối bằng cách ping
            is_connected = await asyncio.wait_for(
                self.redis_client.ping(),
                timeout=2.0
            )
            if not is_connected:
                logger.warning("Redis connection lost, reconnecting...")
                self._initialize_connection()
        except Exception as e:
            logger.warning(f"Thử kết nối lại Redis: {str(e)}")
            self._initialize_connection()

    def generate_cache_key(self, prefix: str, *args) -> str:
        """
        Tạo cache key từ prefix và các tham số.
        """
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

    async def close(self):
        """
        Đóng kết nối Redis khi shutdown
        """
        if hasattr(self, 'redis_client'):
            await self.redis_client.close()
            logger.info("Redis connection closed")