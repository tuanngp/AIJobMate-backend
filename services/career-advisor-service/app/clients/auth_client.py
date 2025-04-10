from typing import Dict, Any, List
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

class AuthClient:
    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_user_info(self, header_user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and return user info từ request header.
        """
        if not header_user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing user info in request header"
            )
        return header_user_info

    async def get_user_info_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin user theo ID từ auth service.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy người dùng"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Lỗi khi lấy thông tin người dùng"
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Không thể kết nối tới auth service"
            )

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lấy danh sách users từ auth service.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users",
                params={"skip": skip, "limit": limit}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Lỗi khi lấy danh sách người dùng"
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Không thể kết nối tới auth service"
            )

    async def close(self):
        """
        Đóng HTTP client.
        """
        await self.client.aclose()

# Global instance
auth_client = AuthClient()