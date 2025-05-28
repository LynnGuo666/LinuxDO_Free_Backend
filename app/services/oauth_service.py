import httpx
import json
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from app.core.config import settings
from app.schemas.schemas import LinuxDOUserInfo, LinuxDOUserSummary


class OAuthService:
    def __init__(self):
        self.client_id = settings.linuxdo_client_id
        self.client_secret = settings.linuxdo_client_secret
        self.redirect_uri = settings.linuxdo_redirect_uri
        
    def get_authorization_url(self, state: str) -> str:
        """获取OAuth授权URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{settings.linuxdo_authorize_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[str]:
        """用授权码换取access_token"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.post(
                    settings.linuxdo_token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                print(f"Token request URL: {settings.linuxdo_token_url}")
                print(f"Token request data: {data}")
                print(f"Token response status: {response.status_code}")
                print(f"Token response text: {response.text}")
                response.raise_for_status()
                token_data = response.json()
                return token_data.get("access_token")
            except Exception as e:
                print(f"Token exchange error: {e}")
                if hasattr(e, 'response'):
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response text: {e.response.text}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[LinuxDOUserInfo]:
        """获取用户基本信息"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.get(
                    settings.linuxdo_user_info_url,
                    headers=headers
                )
                response.raise_for_status()
                user_data = response.json()
                return LinuxDOUserInfo(**user_data)
            except Exception as e:
                print(f"User info error: {e}")
                return None
    
    async def get_user_summary(self, username: str) -> Optional[LinuxDOUserSummary]:
        """获取用户详细统计信息（用于高级模式验证）"""
        url = settings.linuxdo_user_summary_url.format(username=username)
        
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                summary_data = response.json()
                
                # 提取user_summary部分
                if "user_summary" in summary_data:
                    summary = summary_data["user_summary"]
                    return LinuxDOUserSummary(**summary)
                return None
            except Exception as e:
                print(f"User summary error: {e}")
                return None


oauth_service = OAuthService()
