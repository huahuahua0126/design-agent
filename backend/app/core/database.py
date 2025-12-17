"""
数据库配置 - SQLite 本地开发版
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs("./data", exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)


# 确保数据目录存在
ensure_data_dir()

# 创建异步引擎 - SQLite 配置
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    # SQLite 特有配置
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 为 tools 提供的会话上下文管理器
from contextlib import asynccontextmanager


@asynccontextmanager
async def get_db_session():
    """获取数据库会话上下文管理器（用于 tools）"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
