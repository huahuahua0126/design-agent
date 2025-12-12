"""
设计需求自动化分析与交付 Agent 系统 - 后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, requirements, tasks, reports, admin, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时清理资源
    await engine.dispose()


app = FastAPI(
    title="设计需求 Agent 系统",
    description="对话式需求采集、智能派单、状态管理和效能统计",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["需求管理"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务管理"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表统计"])
app.include_router(admin.router, prefix="/api/admin", tags=["系统管理"])
app.include_router(chat.router, prefix="/api/agent", tags=["AI Agent"])


@app.get("/")
async def root():
    return {"message": "设计需求 Agent 系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
