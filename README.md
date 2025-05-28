# LinuxDO福利分发平台

基于FastAPI开发的CDKEY/福利分发平台后端，支持LinuxDO论坛OAuth认证。

## 功能特性

- 📝 OAuth2认证集成LinuxDO论坛
- 🎁 福利/CDKEY创建和分发
- 👥 用户信任等级管理
- 🔒 权限控制和频率限制
- 📊 详细用户数据验证（高级模式）

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件配置必要参数
```

3. 初始化数据库
```bash
alembic upgrade head
```

4. 运行应用
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## OAuth配置

使用LinuxDO论坛的OAuth2认证：
- 授权端点: https://connect.linux.do/oauth2/authorize
- Token端点: https://connect.linux.do/oauth2/token  
- 用户信息端点: https://connect.linux.do/api/user

## 项目结构

```
├── app/
│   ├── api/          # API路由
│   ├── core/         # 核心配置
│   ├── db/           # 数据库相关
│   ├── models/       # 数据模型
│   ├── schemas/      # Pydantic模式
│   └── services/     # 业务逻辑
├── alembic/          # 数据库迁移
├── main.py           # 应用入口
└── requirements.txt  # 依赖包
```
