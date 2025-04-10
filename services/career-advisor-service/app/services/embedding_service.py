import logging
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
    def get_instance(cls) -> 'EmbeddingService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Khởi tạo model sentence-transformer.
        Sử dụng mô hình VoVanPhuc/sup-SimCSE-VietNamese-MultilingualMiniLMv2 vì:
        - Được huấn luyện trên dữ liệu song ngữ Việt-Anh
        - Base model là multilingual-MiniLM-L12-v2
        - Hiểu tốt cả tiếng Việt và tiếng Anh
        - Hỗ trợ cross-lingual semantic search
        - Kích thước nhỏ (~120MB)
        - Tốc độ xử lý nhanh
        - Phù hợp cho ứng dụng tuyển dụng đa ngôn ngữ
        """
        if EmbeddingService._model is None:
            try:
                EmbeddingService._model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-MultilingualMiniLMv2')
                logger.info("Đã khởi tạo Vietnamese-English embedding model thành công")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo embedding model: {str(e)}")
                raise

    def create_embedding(self, text: str) -> List[float]:
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
            cached_embedding = redis_service.get_cache(cache_key)
            
            if cached_embedding:
                return cached_embedding

            # Tạo embedding
            embedding = self._model.encode(text)
            
            # Chuẩn hóa vector (L2 normalization)
            embedding = embedding / np.linalg.norm(embedding)
            
            # Cache kết quả
            embedding_list = embedding.tolist()
            redis_service.set_cache(cache_key, embedding_list, expiry=86400)  # Cache 24h
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo embedding: {str(e)}")
            raise

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Tạo embedding vectors cho nhiều văn bản.
        
        Args:
            texts: Danh sách văn bản cần tạo embedding
            
        Returns:
            List[List[float]]: Danh sách các vector embedding
        """
        try:
            # Kiểm tra cache cho từng text
            redis_service = RedisService.get_instance()
            results = []
            texts_to_encode = []
            indices_to_encode = []
            
            for i, text in enumerate(texts):
                cache_key = redis_service.generate_cache_key("embedding", text[:50])
                cached_embedding = redis_service.get_cache(cache_key)
                
                if cached_embedding:
                    results.append(cached_embedding)
                else:
                    texts_to_encode.append(text)
                    indices_to_encode.append(i)
                    results.append(None)
            
            # Nếu có texts chưa được cache
            if texts_to_encode:
                # Tạo embeddings cho batch
                embeddings = self._model.encode(texts_to_encode)
                
                # Chuẩn hóa vectors
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
                
                # Cache và cập nhật kết quả
                for idx, embedding in zip(indices_to_encode, embeddings):
                    embedding_list = embedding.tolist()
                    cache_key = redis_service.generate_cache_key("embedding", texts[idx][:50])
                    redis_service.set_cache(cache_key, embedding_list, expiry=86400)
                    results[idx] = embedding_list
            
            return results
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo embeddings: {str(e)}")
            raise

    def cross_lingual_similarity(self, vi_text: str, en_text: str) -> float:
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
            vi_embedding = redis_service.get_cache(vi_cache_key)
            en_embedding = redis_service.get_cache(en_cache_key)
            
            # Tạo và cache embeddings nếu chưa có
            if not vi_embedding:
                vi_embedding = self.create_embedding(vi_text)
                redis_service.set_cache(vi_cache_key, vi_embedding, expiry=86400)
                
            if not en_embedding:
                en_embedding = self.create_embedding(en_text)
                redis_service.set_cache(en_cache_key, en_embedding, expiry=86400)
            
            # Tính cosine similarity
            return self.calculate_similarity(vi_embedding, en_embedding)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính cross-lingual similarity: {str(e)}")
            raise

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Tính độ tương đồng cosine giữa hai embedding vectors.
        
        Args:
            embedding1: Vector embedding thứ nhất
            embedding2: Vector embedding thứ hai
            
        Returns:
            float: Độ tương đồng cosine (0-1)
        """
        try:
            # Chuyển về numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Tính cosine similarity
            similarity = np.dot(vec1, vec2)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Lỗi khi tính similarity: {str(e)}")
            raise