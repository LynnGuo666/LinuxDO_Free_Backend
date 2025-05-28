from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.core.security import verify_token
from app.services.user_service import user_service
from app.models.models import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """获取当前认证用户"""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """获取可选的当前用户（允许匿名访问）"""
    if token is None:
        return None
    
    try:
        payload = verify_token(token.credentials)
        if payload is None:
            return None
        
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        
        user = user_service.get_user_by_id(db, user_id=user_id)
        return user
    except Exception:
        return None
