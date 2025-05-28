from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.schemas.schemas import (
    Benefit, BenefitCreate, BenefitUpdate, BenefitClaim, 
    BenefitEligibility, ApiResponse, User
)
from app.services.benefit_service import benefit_service
from app.api.deps import get_current_user, get_optional_current_user

router = APIRouter()


@router.get("/", response_model=List[Benefit])
async def get_benefits(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取活跃的福利列表"""
    benefits = benefit_service.get_active_benefits(db, skip, limit)
    return benefits


@router.post("/", response_model=Benefit)
async def create_benefit(
    benefit_data: BenefitCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新福利"""
    benefit = benefit_service.create_benefit(db, benefit_data, current_user.id)
    return benefit


@router.get("/my", response_model=List[Benefit])
async def get_my_benefits(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我创建的福利"""
    benefits = benefit_service.get_user_benefits(db, current_user.id, skip, limit)
    return benefits


@router.get("/{benefit_id}", response_model=Benefit)
async def get_benefit(
    benefit_id: int,
    db: Session = Depends(get_db)
):
    """获取福利详情"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    return benefit


@router.put("/{benefit_id}", response_model=Benefit)
async def update_benefit(
    benefit_id: int,
    benefit_data: BenefitUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新福利（仅创建者可更新）"""
    benefit = benefit_service.update_benefit(db, benefit_id, benefit_data, current_user.id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found or you don't have permission to update it"
        )
    return benefit


@router.get("/{benefit_id}/eligibility", response_model=BenefitEligibility)
async def check_benefit_eligibility(
    benefit_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查用户是否有资格领取福利"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    
    eligibility = await benefit_service.check_eligibility(db, current_user, benefit)
    return eligibility


@router.post("/{benefit_id}/claim", response_model=ApiResponse)
async def claim_benefit(
    benefit_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """领取福利"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    
    # 先检查资格
    eligibility = await benefit_service.check_eligibility(db, current_user, benefit)
    if not eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=eligibility.reason,
            headers={"X-Missing-Requirements": str(eligibility.missing_requirements) if eligibility.missing_requirements else ""}
        )
    
    # 领取福利
    claim = await benefit_service.claim_benefit(db, current_user, benefit_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim benefit"
        )
    
    return ApiResponse(
        success=True,
        message="福利领取成功！",
        data={
            "benefit_id": benefit_id,
            "content": benefit.content,
            "claimed_at": claim.claimed_at.isoformat()
        }
    )


@router.get("/{benefit_id}/claims", response_model=List[BenefitClaim])
async def get_benefit_claims(
    benefit_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取福利的领取记录（仅创建者可查看）"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    
    if benefit.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this benefit's claims"
        )
    
    claims = benefit_service.get_benefit_claims(db, benefit_id, skip, limit)
    return claims
