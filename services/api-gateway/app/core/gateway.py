from typing import Dict, Optional, Any
import json
import httpx
from fastapi import Request, HTTPException, status
from app.core.config import settings

class GatewayHandler:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.service_routes = {
            # Auth service routes
            path: settings.AUTH_SERVICE_URL
            for path in settings.AUTH_PATHS
        } | {
            # Career Advisor routes
            path: settings.CAREER_ADVISOR_SERVICE_URL
            for path in settings.CAREER_ADVISOR_PATHS
        } | {
            # Interview service routes
            path: settings.INTERVIEW_SERVICE_URL
            for path in settings.INTERVIEW_PATHS
        }

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token với auth service.
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.client.get(
                f"{settings.AUTH_SERVICE_URL}/auth/verify",
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
        """
        for route_prefix, service_url in self.service_routes.items():
            if path.startswith(route_prefix):
                return service_url
        return None

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

    async def handle_request(self, request: Request) -> httpx.Response:
        """
        Xử lý request: auth, route và forward.
        """
        # Xác định target service
        target_service = self.get_target_service(request.url.path)
        if not target_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service không tồn tại"
            )

        # Setup headers to forward
        headers = dict(request.headers)
        auth_header = headers.get("authorization")

        # Verify token nếu có và không phải là request tới /auth/login hoặc /auth/register
        if auth_header and not request.url.path.endswith(("/login", "/register")):
            token = auth_header.split(" ")[1]
            user_info = await self.verify_token(token)
            
            # Thêm user info vào header để forward
            headers["X-User-Info"] = json.dumps(user_info)

        # Forward request
        response = await self.forward_request(request, target_service, headers)
        return response

    async def close(self):
        """
        Đóng HTTP client.
        """
        await self.client.aclose()

# Global instance
gateway_handler = GatewayHandler()