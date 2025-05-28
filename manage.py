#!/usr/bin/env python3
"""
LinuxDO福利分发平台管理工具
用于创建测试数据和管理用户
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.models import User, Benefit, BenefitMode
from app.schemas.schemas import BenefitCreate
from app.services.benefit_service import benefit_service


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def create_test_benefits():
    """创建一些测试福利"""
    db = get_db()
    
    # 创建一个测试用户作为福利创建者
    test_user = db.query(User).first()
    if not test_user:
        print("❌ 没有找到用户，请先通过OAuth登录一次")
        return
    
    # 创建普通模式福利
    normal_benefit = BenefitCreate(
        title="🎁 新手福利包",
        description="欢迎新用户！这是一个普通模式的福利，只需要信任等级0即可领取。",
        content="恭喜获得新手福利包！\n\n内容包含：\n- 学习资料大礼包\n- 社区使用指南\n- 专属新手头像框",
        mode=BenefitMode.NORMAL,
        min_trust_level=0,
        max_claims=100
    )
    
    # 创建需要Level 2的普通福利
    level2_benefit = BenefitCreate(
        title="🚀 成员专享福利",
        description="只有Level 2及以上成员才能领取的福利。",
        content="恭喜获得成员专享福利！\n\nCDKEY: MEMBER-2024-GIFT\n有效期至：2024年12月31日",
        mode=BenefitMode.NORMAL,
        min_trust_level=2,
        max_claims=50
    )
    
    # 创建高级模式福利
    advanced_benefit = BenefitCreate(
        title="🏆 活跃用户奖励",
        description="高级模式福利，需要满足详细的活跃度要求。",
        content="恭喜获得活跃用户奖励！\n\n奖励内容：\n- 高级功能访问权限\n- 专属勋章\n- VIP客服支持\n\nCDKEY: ACTIVE-USER-2024",
        mode=BenefitMode.ADVANCED,
        min_trust_level=1,
        min_likes_given=50,
        min_likes_received=20,
        min_topics_entered=100,
        min_posts_read=500,
        min_days_visited=30,
        min_post_count=10,
        min_time_read=3600,  # 1小时
        max_claims=20
    )
    
    # 创建秦始皇专属福利
    emperor_benefit = BenefitCreate(
        title="👑 秦始皇专属福利",
        description="只有传说中的秦始皇（Level 5）才能领取的神秘福利。",
        content="恭喜您，秦始皇陛下！\n\n🏆 您获得了至高无上的奖励：\n- 论坛终身VIP权限\n- 专属皇冠标识\n- 无限制功能访问\n- 神秘彩蛋解锁\n\nCDKEY: EMPEROR-ULTIMATE-2024\n\n愿您统一六国，一统天下！",
        mode=BenefitMode.NORMAL,
        min_trust_level=5,
        max_claims=1  # 限量1个，物以稀为贵
    )
    
    benefits_to_create = [normal_benefit, level2_benefit, advanced_benefit, emperor_benefit]
    
    for benefit_data in benefits_to_create:
        try:
            benefit = benefit_service.create_benefit(db, benefit_data, test_user.id)
            print(f"✅ 成功创建福利: {benefit.title}")
        except Exception as e:
            print(f"❌ 创建福利失败: {benefit_data.title}, 错误: {e}")
    
    db.close()
    print(f"\n🎉 测试福利创建完成！")


def list_users():
    """列出所有用户"""
    db = get_db()
    users = db.query(User).all()
    
    if not users:
        print("📝 暂无用户数据")
        return
    
    print("👥 用户列表:")
    print("-" * 80)
    print(f"{'ID':<5} {'LinuxDO ID':<12} {'用户名':<20} {'昵称':<15} {'信任等级':<10} {'高级模式'}")
    print("-" * 80)
    
    for user in users:
        advanced_status = "✅" if user.advanced_mode_agreed else "❌"
        print(f"{user.id:<5} {user.linuxdo_id:<12} {user.username:<20} {user.name or 'N/A':<15} Level {user.trust_level:<6} {advanced_status}")
    
    db.close()


def list_benefits():
    """列出所有福利"""
    db = get_db()
    benefits = db.query(Benefit).all()
    
    if not benefits:
        print("🎁 暂无福利数据")
        return
    
    print("🎁 福利列表:")
    print("-" * 100)
    print(f"{'ID':<5} {'标题':<25} {'模式':<10} {'最低等级':<10} {'领取数':<10} {'状态'}")
    print("-" * 100)
    
    for benefit in benefits:
        status = "✅ 活跃" if benefit.is_active else "❌ 停用"
        claims_info = f"{benefit.total_claims}"
        if benefit.max_claims:
            claims_info += f"/{benefit.max_claims}"
        
        print(f"{benefit.id:<5} {benefit.title[:23]:<25} {benefit.mode.value:<10} Level {benefit.min_trust_level:<7} {claims_info:<10} {status}")
    
    db.close()


def main():
    if len(sys.argv) < 2:
        print("📋 LinuxDO福利分发平台管理工具")
        print("\n使用方法:")
        print("  python manage.py create-benefits  # 创建测试福利")
        print("  python manage.py list-users       # 列出所有用户")
        print("  python manage.py list-benefits    # 列出所有福利")
        return
    
    command = sys.argv[1]
    
    if command == "create-benefits":
        create_test_benefits()
    elif command == "list-users":
        list_users()
    elif command == "list-benefits":
        list_benefits()
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
