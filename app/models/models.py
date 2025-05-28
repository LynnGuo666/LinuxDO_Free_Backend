from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class UserTrustLevel(enum.IntEnum):
    LEVEL_0 = 0  # 新用户
    LEVEL_1 = 1  # 基础用户
    LEVEL_2 = 2  # 成员
    LEVEL_3 = 3  # 资深成员
    LEVEL_4 = 4  # 管理员
    LEVEL_5 = 5  # 秦始皇
    


class BenefitMode(enum.Enum):
    NORMAL = "normal"      # 普通模式：仅检查信任等级
    ADVANCED = "advanced"  # 高级模式：获取详细数据验证


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    linuxdo_id = Column(Integer, unique=True, index=True, nullable=False)  # LinuxDO用户ID
    username = Column(String(255), index=True, nullable=False)  # LinuxDO用户名
    name = Column(String(255), nullable=True)  # 用户昵称
    trust_level = Column(Integer, default=0)  # 信任等级 0-4
    is_active = Column(Boolean, default=True)
    is_silenced = Column(Boolean, default=False)
    advanced_mode_agreed = Column(Boolean, default=False)  # 是否同意高级模式协议
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    created_benefits = relationship("Benefit", back_populates="creator")
    claimed_benefits = relationship("BenefitClaim", back_populates="user")


class Benefit(Base):
    __tablename__ = "benefits"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # 福利标题
    description = Column(Text, nullable=True)    # 福利描述
    content = Column(Text, nullable=False)       # 福利内容（CDKEY等）
    
    # 权限配置
    mode = Column(SQLEnum(BenefitMode), default=BenefitMode.NORMAL)  # 模式
    min_trust_level = Column(Integer, default=0)  # 最低信任等级
    
    # 高级模式验证条件
    min_likes_given = Column(Integer, nullable=True)      # 最少给出赞数
    min_likes_received = Column(Integer, nullable=True)   # 最少收到赞数
    min_topics_entered = Column(Integer, nullable=True)   # 最少浏览话题数
    min_posts_read = Column(Integer, nullable=True)       # 最少阅读帖子数
    min_days_visited = Column(Integer, nullable=True)     # 最少访问天数
    min_topic_count = Column(Integer, nullable=True)      # 最少发起话题数
    min_post_count = Column(Integer, nullable=True)       # 最少发帖数
    min_time_read = Column(Integer, nullable=True)        # 最少阅读时间(秒)
    
    # 状态
    is_active = Column(Boolean, default=True)
    total_claims = Column(Integer, default=0)      # 总领取次数
    max_claims = Column(Integer, nullable=True)    # 最大领取次数限制
    
    # 创建者
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    creator = relationship("User", back_populates="created_benefits")
    claims = relationship("BenefitClaim", back_populates="benefit")


class BenefitClaim(Base):
    __tablename__ = "benefit_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    benefit_id = Column(Integer, ForeignKey("benefits.id"), nullable=False)
    
    # 领取时的用户数据快照（高级模式）
    snapshot_data = Column(Text, nullable=True)  # JSON格式存储
    
    claimed_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    user = relationship("User", back_populates="claimed_benefits")
    benefit = relationship("Benefit", back_populates="claims")
