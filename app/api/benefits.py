from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.schemas.schemas import (
    Benefit, BenefitCreate, BenefitUpdate, BenefitClaim, 
    BenefitEligibility, ApiResponse, User, BenefitAccessRequest,
    CDKeyClaimResult, BenefitCDKey, PersonalBlacklistCreate,
    PersonalBlacklist, CreatorStats
)
from app.services.benefit_service import benefit_service
from app.api.deps import get_current_user, get_optional_current_user

router = APIRouter()


@router.get("/", response_model=List[Benefit])
async def get_benefits(
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取公开的活跃福利列表"""
    benefits = benefit_service.get_public_benefits(db, current_user, skip, limit)
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


@router.get("/my/stats", response_model=CreatorStats)
async def get_my_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的创建者统计"""
    from app.models.models import Benefit, BenefitClaim, BenefitCDKey, PersonalBlacklist
    from sqlalchemy import func
    
    # 总福利数
    total_benefits = db.query(func.count(Benefit.id)).filter(Benefit.creator_id == current_user.id).scalar()
    
    # 总领取次数
    total_claims = db.query(func.sum(Benefit.total_claims)).filter(Benefit.creator_id == current_user.id).scalar() or 0
    
    # CDKEY统计
    total_cdkeys = db.query(func.count(BenefitCDKey.id)).join(Benefit).filter(Benefit.creator_id == current_user.id).scalar()
    available_cdkeys = db.query(func.count(BenefitCDKey.id)).join(Benefit).filter(
        Benefit.creator_id == current_user.id,
        BenefitCDKey.is_claimed == False
    ).scalar()
    
    # 黑名单用户数
    blacklisted_users = db.query(func.count(PersonalBlacklist.id)).filter(PersonalBlacklist.creator_id == current_user.id).scalar()
    
    return CreatorStats(
        total_benefits=total_benefits,
        total_claims=total_claims,
        total_cdkeys=total_cdkeys,
        available_cdkeys=available_cdkeys,
        blacklisted_users=blacklisted_users
    )


@router.get("/{benefit_id}", response_model=Benefit)
async def get_benefit(
    benefit_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取福利详情"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id, current_user)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    return benefit


@router.post("/{benefit_id}/access", response_model=Benefit)
async def access_private_benefit(
    benefit_id: int,
    access_request: BenefitAccessRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """访问私有福利（需要密码）"""
    benefit = benefit_service.get_benefit_by_id(db, benefit_id, current_user)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    
    if not benefit_service.verify_benefit_access(db, benefit, access_request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid password for private benefit"
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
    benefit = benefit_service.get_benefit_by_id(db, benefit_id, current_user)
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benefit not found"
        )
    
    eligibility = await benefit_service.check_eligibility(db, current_user, benefit)
    return eligibility


@router.post("/{benefit_id}/claim", response_model=CDKeyClaimResult)
async def claim_benefit(
    benefit_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """领取福利"""
    result = await benefit_service.claim_benefit(db, current_user, benefit_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result


@router.get("/{benefit_id}/claims", response_model=List[BenefitClaim])
async def get_benefit_claims(
    benefit_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取福利的领取记录（仅创建者可查看）"""
    claims = benefit_service.get_benefit_claims(db, benefit_id, current_user.id, skip, limit)
    if not claims and benefit_id:
        # 检查福利是否存在且属于当前用户
        benefit = benefit_service.get_benefit_by_id(db, benefit_id)
        if not benefit or benefit.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benefit not found or you don't have permission to view claims"
            )
    return claims


@router.get("/{benefit_id}/cdkeys", response_model=List[BenefitCDKey])
async def get_benefit_cdkeys(
    benefit_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取福利的CDKEY列表（仅创建者可查看）"""
    cdkeys = benefit_service.get_benefit_cdkeys(db, benefit_id, current_user.id)
    if not cdkeys and benefit_id:
        # 检查福利是否存在且属于当前用户
        benefit = benefit_service.get_benefit_by_id(db, benefit_id)
        if not benefit or benefit.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benefit not found or you don't have permission to view CDKEYs"
            )
    return cdkeys


# 黑名单管理
@router.post("/blacklist", response_model=ApiResponse)
async def add_to_blacklist(
    blacklist_data: PersonalBlacklistCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加用户到个人黑名单"""
    success = benefit_service.add_personal_blacklist(
        db, current_user.id, blacklist_data.blacklisted_user_id, blacklist_data.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in your blacklist"
        )
    
    return ApiResponse(success=True, message="用户已添加到黑名单")


@router.delete("/blacklist/{user_id}", response_model=ApiResponse)
async def remove_from_blacklist(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """从个人黑名单移除用户"""
    success = benefit_service.remove_personal_blacklist(db, current_user.id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your blacklist"
        )
    
    return ApiResponse(success=True, message="用户已从黑名单移除")


@router.get("/blacklist", response_model=List[PersonalBlacklist])
async def get_my_blacklist(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的个人黑名单"""
    return benefit_service.get_personal_blacklist(db, current_user.id)
