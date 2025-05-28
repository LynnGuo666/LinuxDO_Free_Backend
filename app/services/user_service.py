from sqlalchemy.orm import Session
from typing import Optional
from app.models.models import User
from app.schemas.schemas import UserCreate, UserUpdate, LinuxDOUserInfo


class UserService:
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_linuxdo_id(self, db: Session, linuxdo_id: int) -> Optional[User]:
        """根据LinuxDO ID获取用户"""
        return db.query(User).filter(User.linuxdo_id == linuxdo_id).first()
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """创建新用户"""
        db_user = User(**user_data.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def update_user(self, db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        db_user = self.get_user_by_id(db, user_id)
        if not db_user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    
    def update_user_from_linuxdo(self, db: Session, user: User, linuxdo_info: LinuxDOUserInfo) -> User:
        """根据LinuxDO信息更新用户数据"""
        user.username = linuxdo_info.username
        user.name = linuxdo_info.name
        user.trust_level = linuxdo_info.trust_level
        user.is_active = linuxdo_info.active
        user.is_silenced = linuxdo_info.silenced
        
        db.commit()
        db.refresh(user)
        return user
    
    async def update_user_avatar(self, db: Session, user: User, username: str = None) -> User:
        """更新用户头像"""
        from app.services.oauth_service import oauth_service
        
        # 使用传入的用户名或用户对象的用户名
        target_username = username or user.username
        
        # 获取头像URL
        avatar_url = await oauth_service.get_user_avatar(target_username)
        
        if avatar_url:
            user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)
        
        return user
    
    async def get_user_with_avatar(self, db: Session, user_id: int) -> Optional[User]:
        """获取用户并确保有最新头像"""
        user = self.get_user_by_id(db, user_id)
        if user and not user.avatar_url:
            # 如果没有头像，尝试获取
            user = await self.update_user_avatar(db, user)
        return user
    
    async def create_or_update_user_from_linuxdo(self, db: Session, linuxdo_info: LinuxDOUserInfo) -> User:
        """根据LinuxDO信息创建或更新用户"""
        # 查找现有用户
        user = self.get_user_by_linuxdo_id(db, linuxdo_info.id)
        
        if user:
            # 更新现有用户
            user = self.update_user_from_linuxdo(db, user, linuxdo_info)
        else:
            # 创建新用户
            user_data = UserCreate(
                linuxdo_id=linuxdo_info.id,
                username=linuxdo_info.username,
                name=linuxdo_info.name,
                trust_level=linuxdo_info.trust_level
            )
            user = self.create_user(db, user_data)
            user.is_active = linuxdo_info.active
            user.is_silenced = linuxdo_info.silenced
            db.commit()
            db.refresh(user)
        
        # 获取或更新头像
        if not user.avatar_url:
            user = await self.update_user_avatar(db, user, linuxdo_info.username)
        
        return user
    
    def agree_to_advanced_mode(self, db: Session, user_id: int) -> Optional[User]:
        """用户同意高级模式协议"""
        user = self.get_user_by_id(db, user_id)
        if user:
            user.advanced_mode_agreed = True
            db.commit()
            db.refresh(user)
        return user


user_service = UserService()
