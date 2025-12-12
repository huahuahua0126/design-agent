"""
应用配置
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    APP_NAME: str = "设计需求 Agent 系统"
    DEBUG: bool = True
    
    # 数据库配置 - 使用 SQLite（本地开发）
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/design_agent.db"
    
    # 本地文件存储路径（替代 MinIO）
    UPLOAD_DIR: str = "./data/uploads"
    
    # ChromaDB 本地存储路径（内嵌模式）
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    
    # JWT 配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # Qwen API 配置
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"
    QWEN_VL_MODEL: str = "qwen-vl-max"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
