from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.schemas import User, BenefitClaim, ApiResponse
from app.services.user_service import user_service
from app.services.benefit_service import benefit_service
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/me", response_model=User)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/me/claims", response_model=List[BenefitClaim])
async def get_my_claims(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的领取记录"""
    claims = benefit_service.get_user_claims(db, current_user.id, skip, limit)
    return claims


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户信息（公开信息）"""
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
