from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserTrustLevel(int, Enum):
    LEVEL_0 = 0  # 新用户
    LEVEL_1 = 1  # 基础用户
    LEVEL_2 = 2  # 成员
    LEVEL_3 = 3  # 资深成员
    LEVEL_4 = 4  # 管理员
    LEVEL_5 = 5  # 秦始皇


class BenefitMode(str, Enum):
    NORMAL = "NORMAL"
    ADVANCED = "ADVANCED"


class BenefitType(str, Enum):
    CONTENT = "CONTENT"  # 相同内容（权限查看，无限制）
    CDKEY = "CDKEY"      # CDKEY/兑换链接（一人一个，限量）


class BenefitVisibility(str, Enum):
    PUBLIC = "PUBLIC"    # 公开福利
    PRIVATE = "PRIVATE"  # 非公开福利（需要密码）


class UserBase(BaseModel):
    username: str
    name: Optional[str] = None
    trust_level: int = 0


class UserCreate(UserBase):
    linuxdo_id: int


class UserUpdate(BaseModel):
    name: Optional[str] = None
    trust_level: Optional[int] = None
    is_active: Optional[bool] = None
    is_silenced: Optional[bool] = None
    is_globally_blacklisted: Optional[bool] = None
    advanced_mode_agreed: Optional[bool] = None


class User(UserBase):
    id: int
    linuxdo_id: int
    is_active: bool
    is_silenced: bool
    is_globally_blacklisted: bool
    advanced_mode_agreed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BenefitBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None  # 仅content类型使用
    benefit_type: BenefitType = BenefitType.CONTENT
    visibility: BenefitVisibility = BenefitVisibility.PUBLIC
    access_password: Optional[str] = None  # private类型使用
    mode: BenefitMode = BenefitMode.NORMAL
    min_trust_level: int = 0
    max_claims: Optional[int] = None  # 仅content类型使用


class BenefitCreate(BenefitBase):
    cdkeys: Optional[list[str]] = None  # CDKEY类型时使用
    # 高级模式验证条件
    min_likes_given: Optional[int] = None
    min_likes_received: Optional[int] = None
    min_topics_entered: Optional[int] = None
    min_posts_read: Optional[int] = None
    min_days_visited: Optional[int] = None
    min_topic_count: Optional[int] = None
    min_post_count: Optional[int] = None
    min_time_read: Optional[int] = None


class BenefitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    max_claims: Optional[int] = None


class Benefit(BenefitBase):
    id: int
    is_active: bool
    total_claims: int
    creator_id: int
    created_at: datetime
    updated_at: datetime
    
    # 高级模式条件
    min_likes_given: Optional[int] = None
    min_likes_received: Optional[int] = None
    min_topics_entered: Optional[int] = None
    min_posts_read: Optional[int] = None
    min_days_visited: Optional[int] = None
    min_topic_count: Optional[int] = None
    min_post_count: Optional[int] = None
    min_time_read: Optional[int] = None

    class Config:
        from_attributes = True


class BenefitWithCreator(Benefit):
    creator: User


class BenefitClaimBase(BaseModel):
    benefit_id: int


class BenefitClaim(BenefitClaimBase):
    id: int
    user_id: int
    snapshot_data: Optional[str] = None
    claimed_at: datetime

    class Config:
        from_attributes = True


class BenefitClaimWithDetails(BenefitClaim):
    user: User
    benefit: Benefit


# OAuth相关模式
class OAuthState(BaseModel):
    state: str
    redirect_url: Optional[str] = None


class OAuthCallback(BaseModel):
    code: str
    state: str


class LinuxDOUserInfo(BaseModel):
    id: int
    username: str
    name: str
    active: bool
    trust_level: int
    silenced: bool


class LinuxDOUserSummary(BaseModel):
    likes_given: int
    likes_received: int
    topics_entered: int
    posts_read_count: int
    days_visited: int
    topic_count: int
    post_count: int
    time_read: int
    recent_time_read: int
    bookmark_count: int


# API响应模式
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class BenefitEligibility(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    missing_requirements: Optional[Dict[str, Any]] = None


# CDKEY相关模式
class BenefitCDKey(BaseModel):
    id: int
    benefit_id: int
    cdkey_content: str
    is_claimed: bool
    claimed_by_user_id: Optional[int] = None
    claimed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CDKeyClaimResult(BaseModel):
    success: bool
    cdkey: Optional[str] = None
    message: str


# 黑名单相关模式
class PersonalBlacklistCreate(BaseModel):
    blacklisted_user_id: int
    reason: Optional[str] = None


class PersonalBlacklist(BaseModel):
    id: int
    creator_id: int
    blacklisted_user_id: int
    reason: Optional[str] = None
    created_at: datetime
    blacklisted_user: User

    class Config:
        from_attributes = True


class GlobalBlacklistCreate(BaseModel):
    user_id: int
    reason: Optional[str] = None


class GlobalBlacklist(BaseModel):
    id: int
    user_id: int
    reason: Optional[str] = None
    admin_id: int
    created_at: datetime
    user: User
    admin: User

    class Config:
        from_attributes = True


# 福利访问相关模式
class BenefitAccessRequest(BaseModel):
    password: Optional[str] = None  # 私有福利密码


class BenefitClaimRequest(BaseModel):
    password: Optional[str] = None  # 私有福利密码


# 创建者统计
class CreatorStats(BaseModel):
    total_benefits: int
    total_claims: int
    total_cdkeys: int
    available_cdkeys: int
    blacklisted_users: int
