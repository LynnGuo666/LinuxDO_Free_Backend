from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.api import api_router
from app.db.database import engine
from app.models.models import Base

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="基于FastAPI开发的CDKEY/福利分发平台，支持LinuxDO论坛OAuth认证",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix="/api/v1")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    """提供前端页面"""
    return FileResponse('static/index.html')


@app.get("/demo")
async def demo_page():
    """演示页面"""
    return FileResponse('static/index.html')


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": settings.app_name}
