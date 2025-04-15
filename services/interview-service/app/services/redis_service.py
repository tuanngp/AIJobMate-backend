import json
import logging
import hashlib
from typing import Any, Dict, Optional

import redis

from app.core.config import settings

# Cấu hình logging
logger = logging.getLogger(__name__)

class RedisService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        """
        Khởi tạo kết nối với Redis
        """
        self.redis_client = None
        self.is_connected = False
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,  # Timeout ngắn hơn để tránh treo ứng dụng
                socket_timeout=2
            )
            # Kiểm tra kết nối
            self.redis_client.ping()
            self.is_connected = True
            logger.info(f"Đã kết nối Redis tại {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Không thể kết nối Redis: {str(e)}. Tiếp tục hoạt động mà không có cache.")
        except Exception as e:
            logger.error(f"Lỗi kết nối Redis: {str(e)}")
            
    def generate_cache_key(self, prefix: str, *args: Any) -> str:
        """
        Tạo key cho cache dựa trên prefix và các tham số đầu vào
        """
        key = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        if len(key) > 100:  # Nếu key quá dài, dùng hash
            key = f"{prefix}:{hashlib.md5(key.encode()).hexdigest()}"
        return key
    
    def set_cache(self, key: str, data: Any, expiry: int = 3600) -> bool:
        """
        Lưu dữ liệu vào cache
        """
        if not self.is_connected or self.redis_client is None:
            return False
            
        try:
            # Chuyển đổi dữ liệu sang JSON string
            json_data = json.dumps(data, ensure_ascii=False)
            # Lưu vào Redis
            self.redis_client.set(key, json_data, ex=expiry)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cache: {str(e)}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Lấy dữ liệu từ cache
        """
        if not self.is_connected or self.redis_client is None:
            return None
            
        try:
            # Lấy dữ liệu từ Redis
            data = self.redis_client.get(key)
            if data:
                # Chuyển đổi từ JSON string sang object
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy cache: {str(e)}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """
        Xóa dữ liệu từ cache
        """
        if not self.is_connected or self.redis_client is None:
            return False
            
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xóa cache: {str(e)}")
            return False 