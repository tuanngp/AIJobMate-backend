from typing import Dict, Optional, Any
import json
import httpx
from fastapi import Request, HTTPException, status
from app.core.config import settings

class GatewayHandler:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.service_routes = settings.route_mapping
        self.public_paths = {
            f"{settings.API_PREFIX}{path}" if not path.startswith(settings.API_PREFIX) and path not in settings.NO_PREFIX_PATHS
            else path for path in settings.PUBLIC_PATHS
        }

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token với auth service.
        """
        try:
            print(f"{settings.AUTH_SERVICE_URL}{settings.API_PREFIX}/auth/verify")
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.get(
                f"{settings.AUTH_SERVICE_URL}{settings.API_PREFIX}/auth/verify",
                headers=headers
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token không hợp lệ hoặc hết hạn",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Lỗi xác thực với auth service",
                )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Không thể kết nối tới auth service",
            )

    def get_target_service(self, path: str) -> Optional[str]:
        """
        Xác định service URL dựa trên path.
        Tối ưu hóa: Sử dụng prefix matching hiệu quả hơn
        """
        if path in self.service_routes:
            return self.service_routes[path]
            
        matched_prefix = ""
        matched_service = None
        
        for route_prefix, service_url in self.service_routes.items():
            if "{" in route_prefix and path.startswith(route_prefix.split("{")[0]):
                prefix_part = route_prefix.split("{")[0]
                if len(prefix_part) > len(matched_prefix):
                    matched_prefix = prefix_part
                    matched_service = service_url
                    
        return matched_service

    async def forward_request(
        self,
        request: Request,
        target_url: str,
        headers: Dict[str, str]
    ) -> httpx.Response:
        """
        Forward request tới service tương ứng.
        """
        # Get request content
        body = await request.body()
        
        # Forward request với method và headers tương ứng
        try:
            response = await self.client.request(
                method=request.method,
                url=f"{target_url}{request.url.path}",
                params=request.query_params,
                headers=headers,
                content=body
            )
            return response
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error forwarding request: {str(e)}"
            )

    def is_public_path(self, path: str) -> bool:
        """
        Kiểm tra xem path có phải là public path không
        """
        # Kiểm tra exact match
        if path in self.public_paths:
            return True
            
        # Kiểm tra pattern match
        for public_path in self.public_paths:
            if "{" in public_path:
                base_path = public_path.split("{")[0]
                if path.startswith(base_path):
                    return True
                    
        return False
    
    async def handle_request(self, request: Request) -> httpx.Response:
        """
        Xử lý request: auth, route và forward.
        """
        path = request.url.path
        
        # Xác định target service
        target_service = self.get_target_service(request.url.path)
        if not target_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service không tồn tại cho path: {path}"
            )

        # Setup headers to forward
        headers = dict(request.headers)
        auth_header = headers.get("authorization")

        # Xác thực token nếu cần
        if not self.is_public_path(path):
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Authorization header is required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            try:
                token = auth_header.split(" ")[1]
                response_data = await self.verify_token(token)
                user_info = response_data.get("data")
                
                if not user_info:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=response_data.get("errors", ""),
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                    
                # Thêm user info vào header để forward
                headers["X-User-ID"] = str(user_info["id"])
                headers["X-User-Roles"] = ",".join(user_info["roles"])
                headers["X-User-Info"] = json.dumps(user_info)
            except IndexError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization format. Use Bearer token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Forward request
        response = await self.forward_request(request, target_service, headers)
        return response

    async def close(self):
        """
        Đóng HTTP client.
        """
        await self.client.aclose()

_gateway_instance = None

def get_gateway_handler() -> GatewayHandler:
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = GatewayHandler()
    return _gateway_instance

gateway_handler = get_gateway_handler()