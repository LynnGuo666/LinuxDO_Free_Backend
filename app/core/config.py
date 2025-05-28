from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "sqlite:///./linuxdo_free.db"
    
    # LinuxDO OAuth配置
    linuxdo_client_id: str
    linuxdo_client_secret: str
    linuxdo_redirect_uri: str
    
    # JWT配置
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # LinuxDO API端点
    linuxdo_authorize_url: str = "https://connect.linux.do/oauth2/authorize"
    linuxdo_token_url: str = "https://connect.linux.do/oauth2/token"
    linuxdo_user_info_url: str = "https://connect.linux.do/api/user"
    linuxdo_user_summary_url: str = "https://linux.do/u/{username}/summary.json"
    
    # 应用配置
    app_name: str = "LinuxDO福利分发平台"
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
