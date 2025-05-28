import json
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Dict, Any
from app.models.models import (
    Benefit, BenefitClaim, BenefitCDKey, User,
    PersonalBlacklist, GlobalBlacklist
)
from app.schemas.schemas import (
    BenefitCreate, BenefitUpdate, BenefitEligibility, 
    LinuxDOUserSummary, CDKeyClaimResult, BenefitAccessRequest
)
from app.services.oauth_service import oauth_service
from app.core.security import verify_password


class BenefitService:
    def get_benefit_by_id(self, db: Session, benefit_id: int, user: Optional[User] = None) -> Optional[Benefit]:
        """根据ID获取福利（考虑权限和可见性）"""
        benefit = db.query(Benefit).filter(Benefit.id == benefit_id).first()
        if not benefit:
            return None
        
        # 检查全局黑名单
        if user and user.is_globally_blacklisted:
            return None
        
        # 检查个人黑名单
        if user and self._is_user_blacklisted(db, benefit.creator_id, user.id):
            return None
        
        return benefit
    
    def get_public_benefits(self, db: Session, user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Benefit]:
        """获取公开的活跃福利列表"""
        query = db.query(Benefit).filter(
            and_(
                Benefit.is_active == True,
                Benefit.visibility == "public"
            )
        )
        
        # 过滤黑名单用户
        if user:
            if user.is_globally_blacklisted:
                return []
            
            # 过滤个人黑名单
            blacklisted_creators = db.query(PersonalBlacklist.creator_id).filter(
                PersonalBlacklist.blacklisted_user_id == user.id
            ).subquery()
            
            query = query.filter(~Benefit.creator_id.in_(blacklisted_creators))
        
        return query.offset(skip).limit(limit).all()
    
    def get_user_benefits(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Benefit]:
        """获取用户创建的福利"""
        return db.query(Benefit).filter(Benefit.creator_id == user_id).offset(skip).limit(limit).all()
    
    def create_benefit(self, db: Session, benefit_data: BenefitCreate, creator_id: int) -> Benefit:
        """创建福利"""
        # 提取CDKEY数据
        cdkeys_data = benefit_data.cdkeys
        benefit_dict = benefit_data.dict(exclude={'cdkeys'})
        
        # 密码加密
        if benefit_dict.get('access_password'):
            from app.core.security import get_password_hash
            benefit_dict['access_password'] = get_password_hash(benefit_dict['access_password'])
        
        db_benefit = Benefit(**benefit_dict, creator_id=creator_id)
        db.add(db_benefit)
        db.flush()  # 获取ID但不提交
        
        # 如果是CDKEY类型，创建CDKEY记录
        if benefit_data.benefit_type == "cdkey" and cdkeys_data:
            for cdkey_content in cdkeys_data:
                cdkey = BenefitCDKey(
                    benefit_id=db_benefit.id,
                    cdkey_content=cdkey_content.strip()
                )
                db.add(cdkey)
        
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
        
        # 密码加密
        if 'access_password' in update_data and update_data['access_password']:
            from app.core.security import get_password_hash
            update_data['access_password'] = get_password_hash(update_data['access_password'])
        
        for field, value in update_data.items():
            setattr(db_benefit, field, value)
        
        db.commit()
        db.refresh(db_benefit)
        return db_benefit
    
    def verify_benefit_access(self, db: Session, benefit: Benefit, access_request: BenefitAccessRequest) -> bool:
        """验证福利访问权限（私有福利密码验证）"""
        if benefit.visibility == "public":
            return True
        
        if benefit.visibility == "private":
            if not access_request.password:
                return False
            return verify_password(access_request.password, benefit.access_password)
        
        return False
    
    def has_user_claimed(self, db: Session, user_id: int, benefit_id: int) -> bool:
        """检查用户是否已领取过该福利"""
        claim = db.query(BenefitClaim).filter(
            and_(BenefitClaim.user_id == user_id, BenefitClaim.benefit_id == benefit_id)
        ).first()
        return claim is not None
    
    def _is_user_blacklisted(self, db: Session, creator_id: int, user_id: int) -> bool:
        """检查用户是否被创建者拉黑"""
        blacklist = db.query(PersonalBlacklist).filter(
            and_(
                PersonalBlacklist.creator_id == creator_id,
                PersonalBlacklist.blacklisted_user_id == user_id
            )
        ).first()
        return blacklist is not None
    
    async def check_eligibility(self, db: Session, user: User, benefit: Benefit) -> BenefitEligibility:
        """检查用户是否有资格领取福利"""
        # 基本检查
        if not benefit.is_active:
            return BenefitEligibility(eligible=False, reason="福利已停用")
        
        # 黑名单检查
        if user.is_globally_blacklisted:
            return BenefitEligibility(eligible=False, reason="您已被全局拉黑")
        
        if self._is_user_blacklisted(db, benefit.creator_id, user.id):
            return BenefitEligibility(eligible=False, reason="您已被该福利创建者拉黑")
        
        if self.has_user_claimed(db, user.id, benefit.id):
            return BenefitEligibility(eligible=False, reason="您已经领取过此福利")
        
        # CDKEY类型检查可用数量
        if benefit.benefit_type == "cdkey":
            available_count = db.query(BenefitCDKey).filter(
                and_(
                    BenefitCDKey.benefit_id == benefit.id,
                    BenefitCDKey.is_claimed == False
                )
            ).count()
            if available_count == 0:
                return BenefitEligibility(eligible=False, reason="CDKEY已被领完")
        
        # CONTENT类型检查最大领取次数
        if benefit.benefit_type == "content":
            if benefit.max_claims and benefit.total_claims >= benefit.max_claims:
                return BenefitEligibility(eligible=False, reason="福利已被领完")
        
        # 检查信任等级
        if user.trust_level < benefit.min_trust_level:
            return BenefitEligibility(
                eligible=False, 
                reason=f"需要信任等级 {benefit.min_trust_level} 及以上，您当前等级为 {user.trust_level}"
            )
        
        # 普通模式只检查信任等级
        if benefit.mode == "normal":
            return BenefitEligibility(eligible=True)
        
        # 高级模式需要检查详细数据
        if benefit.mode == "advanced":
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
    
    async def claim_benefit(self, db: Session, user: User, benefit_id: int) -> CDKeyClaimResult:
        """领取福利"""
        benefit = self.get_benefit_by_id(db, benefit_id, user)
        if not benefit:
            return CDKeyClaimResult(success=False, message="福利不存在")
        
        # 检查资格
        eligibility = await self.check_eligibility(db, user, benefit)
        if not eligibility.eligible:
            return CDKeyClaimResult(success=False, message=eligibility.reason)
        
        # 根据福利类型处理
        if benefit.benefit_type == "content":
            return await self._claim_content_benefit(db, user, benefit)
        elif benefit.benefit_type == "cdkey":
            return await self._claim_cdkey_benefit(db, user, benefit)
        else:
            return CDKeyClaimResult(success=False, message="未知的福利类型")
    
    async def _claim_content_benefit(self, db: Session, user: User, benefit: Benefit) -> CDKeyClaimResult:
        """领取内容类型福利"""
        # 创建领取记录
        snapshot_data = None
        if benefit.mode == "advanced":
            user_summary = await oauth_service.get_user_summary(user.username)
            if user_summary:
                snapshot_data = json.dumps(user_summary.dict())
        
        db_claim = BenefitClaim(
            user_id=user.id,
            benefit_id=benefit.id,
            snapshot_data=snapshot_data
        )
        
        # 更新福利领取次数
        benefit.total_claims += 1
        
        db.add(db_claim)
        db.commit()
        
        return CDKeyClaimResult(
            success=True, 
            cdkey=benefit.content,  # 返回福利内容
            message="领取成功"
        )
    
    async def _claim_cdkey_benefit(self, db: Session, user: User, benefit: Benefit) -> CDKeyClaimResult:
        """领取CDKEY类型福利"""
        # 查找可用的CDKEY
        available_cdkey = db.query(BenefitCDKey).filter(
            and_(
                BenefitCDKey.benefit_id == benefit.id,
                BenefitCDKey.is_claimed == False
            )
        ).first()
        
        if not available_cdkey:
            return CDKeyClaimResult(success=False, message="CDKEY已被领完")
        
        # 标记CDKEY为已领取
        available_cdkey.is_claimed = True
        available_cdkey.claimed_by_user_id = user.id
        from datetime import datetime
        available_cdkey.claimed_at = datetime.utcnow()
        
        # 创建领取记录
        snapshot_data = None
        if benefit.mode == "advanced":
            user_summary = await oauth_service.get_user_summary(user.username)
            if user_summary:
                snapshot_data = json.dumps(user_summary.dict())
        
        db_claim = BenefitClaim(
            user_id=user.id,
            benefit_id=benefit.id,
            cdkey_id=available_cdkey.id,
            snapshot_data=snapshot_data
        )
        
        # 更新福利领取次数
        benefit.total_claims += 1
        
        db.add(db_claim)
        db.commit()
        
        return CDKeyClaimResult(
            success=True, 
            cdkey=available_cdkey.cdkey_content,
            message="领取成功"
        )
    
    def get_user_claims(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[BenefitClaim]:
        """获取用户的领取记录"""
        return db.query(BenefitClaim).filter(BenefitClaim.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_benefit_claims(self, db: Session, benefit_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[BenefitClaim]:
        """获取福利的领取记录（仅创建者可查看）"""
        # 验证是否为福利创建者
        benefit = db.query(Benefit).filter(
            and_(Benefit.id == benefit_id, Benefit.creator_id == user_id)
        ).first()
        
        if not benefit:
            return []
        
        return db.query(BenefitClaim).filter(BenefitClaim.benefit_id == benefit_id).offset(skip).limit(limit).all()
    
    def get_benefit_cdkeys(self, db: Session, benefit_id: int, user_id: int) -> List[BenefitCDKey]:
        """获取福利的CDKEY列表（仅创建者可查看）"""
        # 验证是否为福利创建者
        benefit = db.query(Benefit).filter(
            and_(Benefit.id == benefit_id, Benefit.creator_id == user_id)
        ).first()
        
        if not benefit:
            return []
        
        return db.query(BenefitCDKey).filter(BenefitCDKey.benefit_id == benefit_id).all()
    
    # 黑名单管理
    def add_personal_blacklist(self, db: Session, creator_id: int, blacklisted_user_id: int, reason: str = None) -> bool:
        """添加个人黑名单"""
        # 检查是否已存在
        existing = db.query(PersonalBlacklist).filter(
            and_(
                PersonalBlacklist.creator_id == creator_id,
                PersonalBlacklist.blacklisted_user_id == blacklisted_user_id
            )
        ).first()
        
        if existing:
            return False
        
        blacklist = PersonalBlacklist(
            creator_id=creator_id,
            blacklisted_user_id=blacklisted_user_id,
            reason=reason
        )
        db.add(blacklist)
        db.commit()
        return True
    
    def remove_personal_blacklist(self, db: Session, creator_id: int, blacklisted_user_id: int) -> bool:
        """移除个人黑名单"""
        blacklist = db.query(PersonalBlacklist).filter(
            and_(
                PersonalBlacklist.creator_id == creator_id,
                PersonalBlacklist.blacklisted_user_id == blacklisted_user_id
            )
        ).first()
        
        if not blacklist:
            return False
        
        db.delete(blacklist)
        db.commit()
        return True
    
    def get_personal_blacklist(self, db: Session, creator_id: int) -> List[PersonalBlacklist]:
        """获取个人黑名单"""
        return db.query(PersonalBlacklist).filter(PersonalBlacklist.creator_id == creator_id).all()


benefit_service = BenefitService()
