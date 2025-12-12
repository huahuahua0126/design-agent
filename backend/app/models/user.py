"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from app.core.database import Base


class UserRole(str, PyEnum):
    """用户角色"""
    ADMIN = "admin"           # 管理员
    OPERATOR = "operator"     # 运营
    DESIGNER = "designer"     # 设计师


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default=UserRole.OPERATOR.value, nullable=False)  # SQLite 兼容
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class OperatorDesignerBinding(Base):
    """运营-设计师绑定表"""
    __tablename__ = "operator_designer_bindings"
    
    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, nullable=False, index=True)
    designer_id = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

