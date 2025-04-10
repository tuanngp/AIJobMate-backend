import uvicorn
import os
import secrets
import argparse
from dotenv import load_dotenv
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_env_file():
    """
    Tạo file .env nếu chưa tồn tại
    """
    if not os.path.exists(".env"):
        logger.info("Tạo file .env từ .env.sample...")
        
        # Kiểm tra nếu .env.sample tồn tại
        if os.path.exists(".env.sample"):
            with open(".env.sample", "r") as sample_file:
                env_content = sample_file.read()
            
            # Thêm secret key ngẫu nhiên
            env_content = env_content.replace("your_secret_key_here", secrets.token_urlsafe(32))
            
            with open(".env", "w") as env_file:
                env_file.write(env_content)
            
            logger.info("Đã tạo file .env. Vui lòng cập nhật các thông tin API keys trước khi chạy ứng dụng.")
        else:
            logger.warning("Không tìm thấy file .env.sample. Vui lòng tạo file .env thủ công.")

def main():
    """
    Hàm chính để chạy ứng dụng
    """
    parser = argparse.ArgumentParser(description="Chạy AI Career Advisor Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host để bind server")
    parser.add_argument("--port", type=int, default=8000, help="Port để bind server")
    parser.add_argument("--reload", action="store_true", help="Tự động reload khi code thay đổi")
    
    args = parser.parse_args()
    
    # Tạo file .env nếu chưa tồn tại
    create_env_file()
    
    # Load biến môi trường
    load_dotenv(dotenv_path=".env", override=True)
    
    logger.info(f"Chạy AI Career Advisor Service tại http://{args.host}:{args.port}")
    logger.info("Truy cập http://localhost:8000/docs để xem Swagger UI API documentation")
    
    # Chạy ứng dụng
    uvicorn.run(
        "app.main:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    )

if __name__ == "__main__":
    main() 