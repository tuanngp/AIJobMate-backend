import logging
import asyncio
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any, Union, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from app.services.redis_service import RedisService

# Cấu hình logging
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service để tạo và quản lý embedding vectors cho văn bản.
    Sử dụng mô hình SentenceTransformer để tạo embeddings.
    """
    _instance: Optional['EmbeddingService'] = None
    _model: Optional[SentenceTransformer] = None
    _initialized: bool = False
    _executor: Optional[ThreadPoolExecutor] = None
    
    # Cấu hình cache
    CACHE_EXPIRY = 86400  # 24 giờ
    CACHE_PREFIX = "embedding"
    MAX_CACHE_KEY_LENGTH = 50

    @classmethod
    async def get_instance(cls) -> 'EmbeddingService':
        """
        Lấy singleton instance với async initialization
        
        Returns:
            EmbeddingService: Instance đã được khởi tạo
        """
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize()
        elif not cls._instance._initialized:
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self) -> None:
        """
        Khởi tạo async cho model và các resource cần thiết
        """
        if self._initialized:
            return
            
        try:
            if self._model is None:
                # Khởi tạo model trong ThreadPoolExecutor để không block event loop
                with ThreadPoolExecutor() as executor:
                    self._model = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        lambda: SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
                    )
                
            # Khởi tạo executor cho các tác vụ CPU-bound
            self._executor = ThreadPoolExecutor(max_workers=4)
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo embedding model: {str(e)}", exc_info=True)
            raise

    def __init__(self):
        """
        Khởi tạo instance với model là None, sẽ được initialize sau
        """
        if self._instance is not None:
            raise RuntimeError("EmbeddingService là singleton, sử dụng get_instance()")
        
        # Các thuộc tính sẽ được khởi tạo trong initialize()
        self._initialized = False
        self._redis_service = None

    def __del__(self):
        """
        Dọn dẹp tài nguyên khi instance bị hủy
        """
        if self._executor is not None:
            self._executor.shutdown(wait=False)

    @property
    def redis_service(self):
        """Lazy loading của Redis service"""
        if self._redis_service is None:
            self._redis_service = RedisService.get_instance()
        return self._redis_service

    def _generate_cache_key(self, prefix: str, text: str) -> str:
        """
        Tạo cache key từ prefix và text
        
        Args:
            prefix: Tiền tố cho cache key
            text: Văn bản để tạo key
            
        Returns:
            str: Cache key
        """
        truncated_text = text[:self.MAX_CACHE_KEY_LENGTH]
        return self.redis_service.generate_cache_key(f"{self.CACHE_PREFIX}_{prefix}", truncated_text)

    async def create_embedding(self, text: str) -> List[float]:
        """
        Tạo embedding vector cho văn bản đầu vào.
        
        Args:
            text: Văn bản cần tạo embedding
            
        Returns:
            List[float]: Vector embedding (kích thước 384)
            
        Raises:
            ValueError: Nếu text rỗng hoặc không hợp lệ
            RuntimeError: Nếu có lỗi khi tạo embedding
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text không được rỗng và phải là chuỗi")
            
        try:
            # Kiểm tra cache
            cache_key = self._generate_cache_key("text", text[:self.MAX_CACHE_KEY_LENGTH])
            cached_embedding = await self.redis_service.get_cache(cache_key)
            
            if cached_embedding is not None:
                return cached_embedding

            # Tạo embedding trong executor để không block event loop
            embedding = await asyncio.get_event_loop().run_in_executor(
                self._executor, 
                self._create_embedding_sync, 
                text
            )
            
            # Cache kết quả
            await self.redis_service.set_cache(
                cache_key, 
                embedding, 
                expiry=self.CACHE_EXPIRY
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo embedding: {str(e)}", exc_info=True)
            raise RuntimeError(f"Lỗi khi tạo embedding: {str(e)}")

    def _create_embedding_sync(self, text: str) -> List[float]:
        """
        Hàm đồng bộ để tạo embedding vector
        
        Args:
            text: Văn bản cần tạo embedding
            
        Returns:
            List[float]: Vector embedding đã chuẩn hóa
        """
        # Tạo embedding
        embedding = self._model.encode(text)
        
        # Chuẩn hóa vector (L2 normalization)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo embedding vectors cho nhiều văn bản với hiệu suất tối ưu.
        
        Args:
            texts: Danh sách văn bản cần tạo embedding
            
        Returns:
            List[List[float]]: Danh sách các vector embedding
            
        Raises:
            ValueError: Nếu danh sách text rỗng
            RuntimeError: Nếu có lỗi khi tạo embeddings
        """
        if not texts:
            return []
            
        try:
            # Chuẩn bị kết quả và tracking các text cần encode
            results = [None] * len(texts)
            uncached_texts = []
            uncached_indices = []
            
            # Kiểm tra cache cho mỗi text
            for i, text in enumerate(texts):
                if not text or not isinstance(text, str):
                    results[i] = []  # Trả về vector rỗng cho text không hợp lệ
                    continue
                    
                cache_key = self._generate_cache_key("text", text[:self.MAX_CACHE_KEY_LENGTH])
                cached_embedding = await self.redis_service.get_cache(cache_key)
                
                if cached_embedding:
                    results[i] = cached_embedding
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Tạo embeddings cho các text chưa được cache
            if uncached_texts:
                # Phương thức batch encode
                batch_embeddings = await self._batch_encode_texts(uncached_texts)
                
                # Cập nhật kết quả và cache
                cache_tasks = []
                for idx, embedding in zip(uncached_indices, batch_embeddings):
                    results[idx] = embedding
                    
                    # Tạo task cache nhưng không đợi hoàn thành ngay
                    cache_key = self._generate_cache_key("text", texts[idx][:self.MAX_CACHE_KEY_LENGTH])
                    cache_tasks.append(
                        self.redis_service.set_cache(cache_key, embedding, expiry=self.CACHE_EXPIRY)
                    )
                
                # Đợi tất cả cache tasks hoàn thành bất đồng bộ
                if cache_tasks:
                    await asyncio.gather(*cache_tasks)
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo batch embeddings: {str(e)}", exc_info=True)
            raise RuntimeError(f"Lỗi khi tạo batch embeddings: {str(e)}")

    async def _batch_encode_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Encode một batch các text thành embeddings
        
        Args:
            texts: Danh sách các văn bản cần encode
            
        Returns:
            List[List[float]]: Danh sách các embedding vectors
        """
        # Thực hiện batch encode trong executor
        def batch_encode():
            embeddings = self._model.encode(texts)
            # Chuẩn hóa từng vector
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Tránh chia cho 0
            norms[norms == 0] = 1.0
            normalized = embeddings / norms
            return normalized.tolist()
            
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, batch_encode
        )

    async def cross_lingual_similarity(self, vi_text: str, en_text: str) -> float:
        """
        Tính độ tương đồng giữa văn bản tiếng Việt và tiếng Anh.
        
        Args:
            vi_text: Văn bản tiếng Việt
            en_text: Văn bản tiếng Anh
            
        Returns:
            float: Độ tương đồng ngữ nghĩa (0-1)
            
        Raises:
            ValueError: Nếu text không hợp lệ
        """
        if not vi_text or not en_text:
            raise ValueError("Cả hai văn bản cần được cung cấp")
            
        try:
            # Tạo embeddings cho cả hai văn bản song song
            vi_embedding, en_embedding = await asyncio.gather(
                self.create_embedding(vi_text),
                self.create_embedding(en_text)
            )
            
            # Tính cosine similarity
            return await self.calculate_similarity(vi_embedding, en_embedding)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính cross-lingual similarity: {str(e)}")
            raise

    async def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Tính độ tương đồng cosine giữa hai embedding vectors.
        
        Args:
            embedding1: Vector embedding thứ nhất
            embedding2: Vector embedding thứ hai
            
        Returns:
            float: Độ tương đồng cosine (0-1)
            
        Raises:
            ValueError: Nếu vectors không hợp lệ
        """
        if not embedding1 or not embedding2:
            raise ValueError("Cả hai embedding vectors đều cần được cung cấp")
            
        try:
            # Tính toán trong executor để tránh blocking
            def compute_similarity():
                vec1 = np.array(embedding1)
                vec2 = np.array(embedding2)
                # Clip để đảm bảo giá trị nằm trong khoảng [0, 1]
                similarity = float(np.clip(np.dot(vec1, vec2), 0.0, 1.0))
                return similarity
                
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, compute_similarity
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi tính similarity: {str(e)}", exc_info=True)
            raise RuntimeError(f"Lỗi khi tính similarity: {str(e)}")

    @lru_cache(maxsize=1000)
    def _fast_similarity_cache(self, emb1_key: str, emb2_key: str) -> float:
        """
        Tính toán similarity với in-memory cache (sử dụng cho các truy vấn lặp lại)
        
        Args:
            emb1_key: Khóa đại diện cho embedding 1
            emb2_key: Khóa đại diện cho embedding 2
            
        Returns:
            float: Giá trị similarity đã được cache
        """
        # Phương thức này chỉ dùng để làm cache wrapper,
        # không triển khai thực tế vì cần await các hàm async
        pass

    async def bulk_similarity(self, query_embedding: List[float], 
                             target_embeddings: List[List[float]]) -> List[float]:
        """
        Tính toán độ tương đồng giữa một embedding và nhiều embeddings khác
        
        Args:
            query_embedding: Vector embedding đầu vào
            target_embeddings: Danh sách các vector embedding cần so sánh
            
        Returns:
            List[float]: Danh sách các điểm tương đồng
        """
        try:
            # Tính toán song song
            def compute_bulk_similarities():
                query_vec = np.array(query_embedding)
                target_vecs = np.array(target_embeddings)
                
                # Tính dot product một lần cho tất cả
                similarities = np.dot(target_vecs, query_vec)
                
                # Clip và trả về kết quả
                return np.clip(similarities, 0.0, 1.0).tolist()
            
            return await asyncio.get_event_loop().run_in_executor(
                self._executor, compute_bulk_similarities
            )
            
        except Exception as e:
            logger.error(f"Lỗi khi tính bulk similarity: {str(e)}", exc_info=True)
            raise