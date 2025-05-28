import json
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List, Dict, Any
from app.models.models import Benefit, BenefitClaim, User, BenefitMode
from app.schemas.schemas import (
    BenefitCreate, BenefitUpdate, BenefitEligibility, 
    LinuxDOUserSummary
)
from app.services.oauth_service import oauth_service


class BenefitService:
    def get_benefit_by_id(self, db: Session, benefit_id: int) -> Optional[Benefit]:
        """根据ID获取福利"""
        return db.query(Benefit).filter(Benefit.id == benefit_id).first()
    
    def get_active_benefits(self, db: Session, skip: int = 0, limit: int = 100) -> List[Benefit]:
        """获取活跃的福利列表"""
        return db.query(Benefit).filter(Benefit.is_active == True).offset(skip).limit(limit).all()
    
    def get_user_benefits(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Benefit]:
        """获取用户创建的福利"""
        return db.query(Benefit).filter(Benefit.creator_id == user_id).offset(skip).limit(limit).all()
    
    def create_benefit(self, db: Session, benefit_data: BenefitCreate, creator_id: int) -> Benefit:
        """创建福利"""
        db_benefit = Benefit(**benefit_data.dict(), creator_id=creator_id)
        db.add(db_benefit)
        db.commit()
        db.refresh(db_benefit)
        return db_benefit
    
    def update_benefit(self, db: Session, benefit_id: int, benefit_data: BenefitUpdate, user_id: int) -> Optional[Benefit]:
        """更新福利（仅创建者可更新）"""
        db_benefit = db.query(Benefit).filter(
            and_(Benefit.id == benefit_id, Benefit.creator_id == user_id)
        ).first()
        
        if not db_benefit:
            return None
        
        update_data = benefit_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_benefit, field, value)
        
        db.commit()
        db.refresh(db_benefit)
        return db_benefit
    
    def has_user_claimed(self, db: Session, user_id: int, benefit_id: int) -> bool:
        """检查用户是否已领取过该福利"""
        claim = db.query(BenefitClaim).filter(
            and_(BenefitClaim.user_id == user_id, BenefitClaim.benefit_id == benefit_id)
        ).first()
        return claim is not None
    
    async def check_eligibility(self, db: Session, user: User, benefit: Benefit) -> BenefitEligibility:
        """检查用户是否有资格领取福利"""
        # 基本检查
        if not benefit.is_active:
            return BenefitEligibility(eligible=False, reason="福利已停用")
        
        if self.has_user_claimed(db, user.id, benefit.id):
            return BenefitEligibility(eligible=False, reason="您已经领取过此福利")
        
        if benefit.max_claims and benefit.total_claims >= benefit.max_claims:
            return BenefitEligibility(eligible=False, reason="福利已被领完")
        
        # 检查信任等级
        if user.trust_level < benefit.min_trust_level:
            return BenefitEligibility(
                eligible=False, 
                reason=f"需要信任等级 {benefit.min_trust_level} 及以上，您当前等级为 {user.trust_level}"
            )
        
        # 普通模式只检查信任等级
        if benefit.mode == BenefitMode.NORMAL:
            return BenefitEligibility(eligible=True)
        
        # 高级模式需要检查详细数据
        if benefit.mode == BenefitMode.ADVANCED:
            if not user.advanced_mode_agreed:
                return BenefitEligibility(
                    eligible=False, 
                    reason="需要先同意高级模式协议才能领取此福利"
                )
            
            # 获取用户详细数据
            user_summary = await oauth_service.get_user_summary(user.username)
            if not user_summary:
                return BenefitEligibility(
                    eligible=False, 
                    reason="无法获取您的详细数据，请稍后重试"
                )
            
            # 检查各项条件
            missing_requirements = []
            
            if benefit.min_likes_given and user_summary.likes_given < benefit.min_likes_given:
                missing_requirements.append(f"需要给出 {benefit.min_likes_given} 个赞，当前 {user_summary.likes_given}")
            
            if benefit.min_likes_received and user_summary.likes_received < benefit.min_likes_received:
                missing_requirements.append(f"需要收到 {benefit.min_likes_received} 个赞，当前 {user_summary.likes_received}")
            
            if benefit.min_topics_entered and user_summary.topics_entered < benefit.min_topics_entered:
                missing_requirements.append(f"需要浏览 {benefit.min_topics_entered} 个话题，当前 {user_summary.topics_entered}")
            
            if benefit.min_posts_read and user_summary.posts_read_count < benefit.min_posts_read:
                missing_requirements.append(f"需要阅读 {benefit.min_posts_read} 个帖子，当前 {user_summary.posts_read_count}")
            
            if benefit.min_days_visited and user_summary.days_visited < benefit.min_days_visited:
                missing_requirements.append(f"需要访问 {benefit.min_days_visited} 天，当前 {user_summary.days_visited}")
            
            if benefit.min_topic_count and user_summary.topic_count < benefit.min_topic_count:
                missing_requirements.append(f"需要发起 {benefit.min_topic_count} 个话题，当前 {user_summary.topic_count}")
            
            if benefit.min_post_count and user_summary.post_count < benefit.min_post_count:
                missing_requirements.append(f"需要发布 {benefit.min_post_count} 个帖子，当前 {user_summary.post_count}")
            
            if benefit.min_time_read and user_summary.time_read < benefit.min_time_read:
                missing_requirements.append(f"需要阅读时长 {benefit.min_time_read//60} 分钟，当前 {user_summary.time_read//60} 分钟")
            
            if missing_requirements:
                return BenefitEligibility(
                    eligible=False,
                    reason="不满足高级模式验证条件",
                    missing_requirements={"requirements": missing_requirements}
                )
        
        return BenefitEligibility(eligible=True)
    
    async def claim_benefit(self, db: Session, user: User, benefit_id: int) -> Optional[BenefitClaim]:
        """领取福利"""
        benefit = self.get_benefit_by_id(db, benefit_id)
        if not benefit:
            return None
        
        # 检查资格
        eligibility = await self.check_eligibility(db, user, benefit)
        if not eligibility.eligible:
            return None
        
        # 创建领取记录
        snapshot_data = None
        if benefit.mode == BenefitMode.ADVANCED:
            user_summary = await oauth_service.get_user_summary(user.username)
            if user_summary:
                snapshot_data = json.dumps(user_summary.dict())
        
        db_claim = BenefitClaim(
            user_id=user.id,
            benefit_id=benefit_id,
            snapshot_data=snapshot_data
        )
        
        # 更新福利领取次数
        benefit.total_claims += 1
        
        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)
        
        return db_claim
    
    def get_user_claims(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[BenefitClaim]:
        """获取用户的领取记录"""
        return db.query(BenefitClaim).filter(BenefitClaim.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_benefit_claims(self, db: Session, benefit_id: int, skip: int = 0, limit: int = 100) -> List[BenefitClaim]:
        """获取福利的领取记录"""
        return db.query(BenefitClaim).filter(BenefitClaim.benefit_id == benefit_id).offset(skip).limit(limit).all()


benefit_service = BenefitService()
