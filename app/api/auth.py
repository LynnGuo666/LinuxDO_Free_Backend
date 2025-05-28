import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import Token, ApiResponse, OAuthState
from app.services.oauth_service import oauth_service
from app.services.user_service import user_service
from app.core.security import create_access_token
from app.api.deps import get_current_user

router = APIRouter()

# 临时存储state，生产环境建议使用Redis
oauth_states = {}


@router.get("/login")
async def oauth_login(redirect_url: str = Query(None, description="登录成功后的跳转URL")):
    """发起OAuth登录"""
    state = str(uuid.uuid4())
    oauth_states[state] = {"redirect_url": redirect_url}
    
    auth_url = oauth_service.get_authorization_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态码"),
    db: Session = Depends(get_db)
):
    """OAuth回调处理"""
    # 验证state
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    state_data = oauth_states.pop(state)
    
    try:
        # 用授权码换取access_token
        access_token = await oauth_service.exchange_code_for_token(code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        # 获取用户信息
        user_info = await oauth_service.get_user_info(access_token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        # 创建或更新用户
        user = user_service.create_or_update_user_from_linuxdo(db, user_info)
        
        # 生成JWT Token
        token_data = {"sub": str(user.id)}
        jwt_token = create_access_token(data=token_data)
        
        # 如果有重定向URL，则重定向；否则返回token
        redirect_url = state_data.get("redirect_url")
        if redirect_url:
            # 将token作为查询参数传递（仅用于演示，生产环境建议使用更安全的方式）
            return RedirectResponse(url=f"{redirect_url}?token={jwt_token}")
        
        return Token(
            access_token=jwt_token,
            token_type="bearer",
            expires_in=1440 * 60  # 24小时，秒为单位
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback error: {str(e)}"
        )


@router.post("/agree-advanced-mode")
async def agree_advanced_mode(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同意高级模式协议"""
    user = user_service.agree_to_advanced_mode(db, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return ApiResponse(
        success=True,
        message="已成功同意高级模式协议",
        data={"advanced_mode_agreed": user.advanced_mode_agreed}
    )
