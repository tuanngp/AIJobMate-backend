# Sử dụng multi-stage build để giảm kích thước image

# Stage 1: Build image
FROM python:3.9-slim as builder

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime image
FROM python:3.9-slim

WORKDIR /app

# Cài đặt các gói cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Sao chép wheels từ builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Sao chép mã nguồn ứng dụng
COPY . .

# Tạo người dùng không phải root để chạy ứng dụng
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Thiết lập biến môi trường
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Cổng mà FastAPI chạy
EXPOSE 8000

# Chạy ứng dụng
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 