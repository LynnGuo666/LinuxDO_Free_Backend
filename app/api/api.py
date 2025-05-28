from fastapi import APIRouter
from app.api import auth, users, benefits

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/oauth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(benefits.router, prefix="/benefits", tags=["福利"])
