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
from app.models.models import User, Benefit, BenefitClaim, BenefitMode, BenefitType, BenefitVisibility, BenefitCDKey
from app.schemas.schemas import BenefitCreate
from app.services.benefit_service import benefit_service


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def create_test_user():
    """创建一个测试用户"""
    db = get_db()
    
    # 检查是否已有测试用户
    test_user = db.query(User).filter(User.username == "testuser").first()
    if test_user:
        print("✅ 测试用户已存在")
        return test_user
    
    # 创建测试用户
    test_user = User(
        linuxdo_id=999999,
        username="testuser",
        name="测试用户",
        trust_level=2,  # Level 2 成员
        is_active=True,
        advanced_mode_agreed=True
    )
    
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    print("✅ 成功创建测试用户")
    return test_user


def create_test_user():
    """创建一个测试用户"""
    db = get_db()
    
    # 检查是否已有测试用户
    test_user = db.query(User).filter(User.username == "testuser").first()
    if test_user:
        print("✅ 测试用户已存在")
        db.close()
        return test_user
    
    # 创建测试用户
    test_user = User(
        linuxdo_id=999999,
        username="testuser",
        name="测试用户",
        trust_level=2,  # Level 2 成员
        is_active=True,
        advanced_mode_agreed=True
    )
    
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    db.close()
    print("✅ 成功创建测试用户")
    return test_user


def create_test_benefits():
    """创建一些测试福利"""
    db = get_db()
    
    # 创建或获取测试用户作为福利创建者
    test_user = db.query(User).first()
    if not test_user:
        print("📝 未找到用户，正在创建测试用户...")
        db.close()
        test_user = create_test_user()
        db = get_db()
    
    # 1. 创建内容类型的普通模式福利
    normal_benefit = BenefitCreate(
        title="🎁 新手福利包",
        description="欢迎新用户！这是一个普通模式的福利，只需要信任等级0即可领取。",
        content="恭喜获得新手福利包！\n\n内容包含：\n- 学习资料大礼包\n- 社区使用指南\n- 专属新手头像框",
        benefit_type=BenefitType.CONTENT,
        visibility=BenefitVisibility.PUBLIC,
        mode=BenefitMode.NORMAL,
        min_trust_level=0,
        max_claims=100
    )
    
    # 2. 创建CDKEY类型福利
    cdkey_benefit = BenefitCreate(
        title="🎮 游戏CDKEY大放送",
        description="限量游戏CDKEY，先到先得！每人限领一个。",
        benefit_type=BenefitType.CDKEY,
        visibility=BenefitVisibility.PUBLIC,
        mode=BenefitMode.NORMAL,
        min_trust_level=1,
        cdkeys=[
            "GAME-KEY-001-ABCD-EFGH",
            "GAME-KEY-002-IJKL-MNOP", 
            "GAME-KEY-003-QRST-UVWX",
            "GAME-KEY-004-YZAB-CDEF",
            "GAME-KEY-005-GHIJ-KLMN"
        ]
    )
    
    # 3. 创建私有福利（需要密码）
    private_benefit = BenefitCreate(
        title="🔒 神秘福利",
        description="这是一个神秘的私有福利，需要正确的密码才能查看和领取。密码提示：论坛名称",
        content="恭喜你找到了神秘福利！\n\n🎁 神秘大礼包内容：\n- 限定版徽章\n- 特殊权限\n- 专属头衔\n\n密码是'linuxdo'对吧？",
        benefit_type=BenefitType.CONTENT,
        visibility=BenefitVisibility.PRIVATE,
        access_password="linuxdo",
        mode=BenefitMode.NORMAL,
        min_trust_level=0,
        max_claims=50
    )
    
    # 4. 创建需要Level 2的普通福利
    level2_benefit = BenefitCreate(
        title="🚀 成员专享福利",
        description="只有Level 2及以上成员才能领取的福利。",
        content="恭喜获得成员专享福利！\n\nCDKEY: MEMBER-2024-GIFT\n有效期至：2024年12月31日",
        benefit_type=BenefitType.CONTENT,
        visibility=BenefitVisibility.PUBLIC,
        mode=BenefitMode.NORMAL,
        min_trust_level=2,
        max_claims=50
    )
    
    # 5. 创建高级模式福利
    advanced_benefit = BenefitCreate(
        title="🏆 活跃用户奖励",
        description="高级模式福利，需要满足详细的活跃度要求。",
        content="恭喜获得活跃用户奖励！\n\n奖励内容：\n- 高级功能访问权限\n- 专属勋章\n- VIP客服支持\n\nCDKEY: ACTIVE-USER-2024",
        benefit_type=BenefitType.CONTENT,
        visibility=BenefitVisibility.PUBLIC,
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
    
    # 6. 创建秦始皇专属福利
    emperor_benefit = BenefitCreate(
        title="👑 秦始皇专属福利",
        description="只有传说中的秦始皇（Level 5）才能领取的神秘福利。",
        content="恭喜您，秦始皇陛下！\n\n🏆 您获得了至高无上的奖励：\n- 论坛终身VIP权限\n- 专属皇冠标识\n- 无限制功能访问\n- 神秘彩蛋解锁\n\nCDKEY: EMPEROR-ULTIMATE-2024\n\n愿您统一六国，一统天下！",
        benefit_type=BenefitType.CONTENT,
        visibility=BenefitVisibility.PUBLIC,
        mode=BenefitMode.NORMAL,
        min_trust_level=5,
        max_claims=1  # 限量1个，物以稀为贵
    )
    
    benefits_to_create = [normal_benefit, cdkey_benefit, private_benefit, level2_benefit, advanced_benefit, emperor_benefit]
    
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
    print("-" * 110)
    print(f"{'ID':<5} {'标题':<20} {'类型':<8} {'可见性':<8} {'模式':<8} {'最低等级':<8} {'领取数':<12} {'状态'}")
    print("-" * 110)
    
    for benefit in benefits:
        status = "✅ 活跃" if benefit.is_active else "❌ 停用"
        claims_info = f"{benefit.total_claims}"
        if benefit.max_claims:
            claims_info += f"/{benefit.max_claims}"
        elif benefit.benefit_type == BenefitType.CDKEY:
            # 对于CDKEY类型，显示可用/总数
            total_cdkeys = db.query(BenefitCDKey).filter(BenefitCDKey.benefit_id == benefit.id).count()
            available_cdkeys = db.query(BenefitCDKey).filter(
                BenefitCDKey.benefit_id == benefit.id,
                BenefitCDKey.is_claimed == False
            ).count()
            claims_info = f"{available_cdkeys}/{total_cdkeys}"
        
        benefit_type = "内容" if benefit.benefit_type == BenefitType.CONTENT else "CDKEY"
        visibility = "公开" if benefit.visibility == BenefitVisibility.PUBLIC else "私有"
        mode = "普通" if benefit.mode == BenefitMode.NORMAL else "高级"
        
        print(f"{benefit.id:<5} {benefit.title[:18]:<20} {benefit_type:<8} {visibility:<8} {mode:<8} Level {benefit.min_trust_level:<5} {claims_info:<12} {status}")
    
    db.close()


def list_cdkeys():
    """列出所有CDKEY状态"""
    db = get_db()
    cdkeys = db.query(BenefitCDKey).join(Benefit).all()
    
    if not cdkeys:
        print("🎮 暂无CDKEY数据")
        return
    
    print("🎮 CDKEY列表:")
    print("-" * 120)
    print(f"{'ID':<5} {'福利ID':<8} {'福利标题':<25} {'CDKEY':<25} {'状态':<8} {'领取者':<15} {'领取时间'}")
    print("-" * 120)
    
    for cdkey in cdkeys:
        status = "❌ 已领取" if cdkey.is_claimed else "✅ 可用"
        claimed_by = "N/A"
        claimed_time = "N/A"
        
        if cdkey.is_claimed and cdkey.claimed_by_user_id:
            claimed_user = db.query(User).filter(User.id == cdkey.claimed_by_user_id).first()
            if claimed_user:
                claimed_by = claimed_user.username[:13]
            if cdkey.claimed_at:
                claimed_time = cdkey.claimed_at.strftime("%m-%d %H:%M")
        
        print(f"{cdkey.id:<5} {cdkey.benefit_id:<8} {cdkey.benefit.title[:23]:<25} {cdkey.cdkey_content[:23]:<25} {status:<8} {claimed_by:<15} {claimed_time}")
    
    db.close()


def show_benefit_details(benefit_id: int):
    """显示福利详细信息"""
    db = get_db()
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id).first()
    
    if not benefit:
        print(f"❌ 福利 ID {benefit_id} 不存在")
        return
    
    creator = db.query(User).filter(User.id == benefit.creator_id).first()
    
    print(f"🎁 福利详细信息 (ID: {benefit.id})")
    print("=" * 60)
    print(f"标题: {benefit.title}")
    print(f"描述: {benefit.description}")
    print(f"创建者: {creator.username if creator else 'Unknown'}")
    print(f"类型: {'内容福利' if benefit.benefit_type == BenefitType.CONTENT else 'CDKEY福利'}")
    print(f"可见性: {'公开' if benefit.visibility == BenefitVisibility.PUBLIC else '私有'}")
    print(f"模式: {'普通模式' if benefit.mode == BenefitMode.NORMAL else '高级模式'}")
    print(f"最低信任等级: Level {benefit.min_trust_level}")
    print(f"状态: {'✅ 活跃' if benefit.is_active else '❌ 停用'}")
    print(f"总领取次数: {benefit.total_claims}")
    
    if benefit.max_claims:
        print(f"最大领取次数: {benefit.max_claims}")
    
    if benefit.benefit_type == BenefitType.CONTENT and benefit.content:
        print(f"内容: {benefit.content[:100]}...")
    
    if benefit.benefit_type == BenefitType.CDKEY:
        total_cdkeys = db.query(BenefitCDKey).filter(BenefitCDKey.benefit_id == benefit.id).count()
        available_cdkeys = db.query(BenefitCDKey).filter(
            BenefitCDKey.benefit_id == benefit.id,
            BenefitCDKey.is_claimed == False
        ).count()
        print(f"CDKEY统计: {available_cdkeys}/{total_cdkeys} 可用")
    
    # 高级模式条件
    if benefit.mode == BenefitMode.ADVANCED:
        print("\n🏆 高级模式验证条件:")
        conditions = []
        if benefit.min_likes_given: conditions.append(f"给赞数 ≥ {benefit.min_likes_given}")
        if benefit.min_likes_received: conditions.append(f"收赞数 ≥ {benefit.min_likes_received}")
        if benefit.min_topics_entered: conditions.append(f"浏览话题 ≥ {benefit.min_topics_entered}")
        if benefit.min_posts_read: conditions.append(f"阅读帖子 ≥ {benefit.min_posts_read}")
        if benefit.min_days_visited: conditions.append(f"访问天数 ≥ {benefit.min_days_visited}")
        if benefit.min_topic_count: conditions.append(f"发起话题 ≥ {benefit.min_topic_count}")
        if benefit.min_post_count: conditions.append(f"发布帖子 ≥ {benefit.min_post_count}")
        if benefit.min_time_read: conditions.append(f"阅读时长 ≥ {benefit.min_time_read//60}分钟")
        
        for condition in conditions:
            print(f"  - {condition}")
    
    print(f"\n创建时间: {benefit.created_at}")
    print(f"更新时间: {benefit.updated_at}")
    
    db.close()


def clear_test_data():
    """清理测试数据"""
    db = get_db()
    
    print("⚠️  准备清理所有测试数据...")
    confirm = input("确认清理？这将删除所有福利、CDKEY和领取记录 (y/N): ")
    
    if confirm.lower() != 'y':
        print("❌ 取消清理操作")
        return
    
    try:
        # 删除所有数据
        db.query(BenefitClaim).delete()
        db.query(BenefitCDKey).delete()
        db.query(Benefit).delete()
        db.commit()
        print("✅ 测试数据清理完成")
    except Exception as e:
        db.rollback()
        print(f"❌ 清理失败: {e}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("📋 LinuxDO福利分发平台管理工具")
        print("\n使用方法:")
        print("  python manage.py create-test-user  # 创建测试用户")
        print("  python manage.py create-benefits   # 创建测试福利")
        print("  python manage.py list-users        # 列出:所有用户")
        print("  python manage.py list-benefits     # 列出所有福利")
        print("  python manage.py list-cdkeys       # 列出所有CDKEY状态")
        print("  python manage.py clear-test-data   # 清理测试数据")
        return
    
    command = sys.argv[1]
    
    if command == "create-test-user":
        create_test_user()
    elif command == "create-benefits":
        create_test_benefits()
    elif command == "list-users":
        list_users()
    elif command == "list-benefits":
        list_benefits()
    elif command == "list-cdkeys":
        list_cdkeys()
    elif command == "clear-test-data":
        clear_test_data()
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
