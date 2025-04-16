from concurrent.futures import ThreadPoolExecutor
import logging
import asyncio
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.services.redis_service import RedisService

# Cấu hình logging
logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None

    @classmethod
    async def get_instance(cls) -> 'EmbeddingService':
        """
        Get singleton instance với async initialization
        """
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize()
        return cls._instance

    async def initialize(self):
        """
        Async initialization
        """
        if self._model is None:
            try:
                self._model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo embedding model: {str(e)}")
                raise

    def __init__(self):
        """
        Khởi tạo instance với model là None, sẽ được initialize sau
        """
        if self._instance is not None:
            raise Exception("EmbeddingService là singleton, sử dụng get_instance()")

    async def create_embedding(self, text: str) -> List[float]:
        """
        Tạo embedding vector cho văn bản đầu vào.
        
        Args:
            text: Văn bản cần tạo embedding
            
        Returns:
            List[float]: Vector embedding (kích thước 384)
        """
        try:
            
            # Kiểm tra cache
            redis_service = RedisService.get_instance()
            cache_key = redis_service.generate_cache_key("embedding", text[:50])
            cached_embedding = await redis_service.get_cache(cache_key)
            
            if cached_embedding is not None:
                return cached_embedding

            # Tạo embedding (chạy trong ThreadPoolExecutor để không block event loop)
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                embedding = await asyncio.get_event_loop().run_in_executor(
                    executor, self._model.encode, text
                )
            
            # Chuẩn hóa vector (L2 normalization)
            embedding = embedding / np.linalg.norm(embedding)
            
            # Cache kết quả
            embedding_list = embedding.tolist()
            await redis_service.set_cache(cache_key, embedding_list, expiry=86400)  # Cache 24h
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo embedding: {str(e)}", exc_info=True)
            raise

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo embedding vectors cho nhiều văn bản.
        
        Args:
            texts: Danh sách văn bản cần tạo embedding
            
        Returns:
            List[List[float]]: Danh sách các vector embedding
        """
        try:
            # Kiểm tra cache cho từng text
            # Khởi tạo Redis service
            redis_service = RedisService.get_instance()
            results = []
            texts_to_encode = []
            indices_to_encode = []
            
            # Kiểm tra cache cho mỗi text
            for i, text in enumerate(texts):
                cache_key = redis_service.generate_cache_key("embedding", text[:50])
                cached_embedding = await redis_service.get_cache(cache_key)
                
                if cached_embedding:
                    results.append(cached_embedding)
                else:
                    texts_to_encode.append(text)
                    indices_to_encode.append(i)
                    results.append(None)
            
            # Nếu có texts chưa được cache
            if texts_to_encode:
                # Tạo embeddings cho batch trong ThreadPoolExecutor
                with ThreadPoolExecutor() as executor:
                    embeddings = await asyncio.get_event_loop().run_in_executor(
                        executor, self._model.encode, texts_to_encode
                    )
                
                # Chuẩn hóa vectors
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
                
                # Cache và cập nhật kết quả
                for idx, embedding in zip(indices_to_encode, embeddings):
                    embedding_list = embedding.tolist()
                    cache_key = redis_service.generate_cache_key("embedding", texts[idx][:50])
                    await redis_service.set_cache(cache_key, embedding_list, expiry=86400)
                    results[idx] = embedding_list
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo embeddings: {str(e)}")
            raise

    async def cross_lingual_similarity(self, vi_text: str, en_text: str) -> float:
        """
        Tính độ tương đồng giữa văn bản tiếng Việt và tiếng Anh.
        
        Args:
            vi_text: Văn bản tiếng Việt
            en_text: Văn bản tiếng Anh
            
        Returns:
            float: Độ tương đồng ngữ nghĩa (0-1)
        """
        try:
            # Tạo cache keys
            redis_service = RedisService.get_instance()
            vi_cache_key = redis_service.generate_cache_key("vi_embedding", vi_text[:50])
            en_cache_key = redis_service.generate_cache_key("en_embedding", en_text[:50])
            
            # Kiểm tra cache cho embeddings
            vi_embedding = await redis_service.get_cache(vi_cache_key)
            en_embedding = await redis_service.get_cache(en_cache_key)
            
            # Tạo và cache embeddings nếu chưa có
            if not vi_embedding:
                vi_embedding = await self.create_embedding(vi_text)
                await redis_service.set_cache(vi_cache_key, vi_embedding, expiry=86400)
                
            if not en_embedding:
                en_embedding = await self.create_embedding(en_text)
                await redis_service.set_cache(en_cache_key, en_embedding, expiry=86400)
            
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
        """
        try:
            # Tính toán trong ThreadPoolExecutor để không block event loop
            with ThreadPoolExecutor() as executor:
                def compute_similarity():
                    vec1 = np.array(embedding1)
                    vec2 = np.array(embedding2)
                    similarity = np.dot(vec1, vec2)
                    return float(similarity)
                
                return await asyncio.get_event_loop().run_in_executor(
                    executor, compute_similarity
                )
            
        except Exception as e:
            logger.error(f"Lỗi khi tính similarity: {str(e)}")
            raise