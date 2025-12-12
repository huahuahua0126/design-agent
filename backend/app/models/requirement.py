"""
需求单模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from app.core.database import Base


class RequirementType(str, PyEnum):
    """需求类型"""
    BANNER = "banner"
    POSTER = "poster"
    DETAIL_PAGE = "detail_page"
    ICON = "icon"
    OTHER = "other"


class TaskStatus(str, PyEnum):
    """任务状态"""
    PENDING = "pending"           # 待接单
    IN_PROGRESS = "in_progress"   # 进行中
    UNDER_REVIEW = "under_review" # 待验收
    REVISING = "revising"         # 修改中
    COMPLETED = "completed"       # 已完成


class Requirement(Base):
    """需求单表"""
    __tablename__ = "requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    requirement_type = Column(String(20), default=RequirementType.OTHER.value)  # SQLite 兼容
    dimensions = Column(String(50))  # 如 "1080x640"
    deadline = Column(DateTime)  # SQLite 不支持 timezone
    copywriting = Column(Text)  # 文案内容
    reference_images = Column(JSON, default=list)  # 参考图 URLs
    additional_notes = Column(Text)  # 补充说明
    
    # 派单信息
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    designer_id = Column(Integer, ForeignKey("users.id"))
    estimated_hours = Column(Float)  # 预估工时
    
    # 状态
    status = Column(String(20), default=TaskStatus.PENDING.value)  # SQLite 兼容
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 对话历史 ID (用于 LangGraph Checkpointer)
    conversation_id = Column(String(100))


class TaskTimeLog(Base):
    """任务计时记录"""
    __tablename__ = "task_time_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), nullable=False)
    action = Column(String(20), nullable=False)  # start/pause/resume/complete
    timestamp = Column(DateTime, server_default=func.now())
    accumulated_hours = Column(Float, default=0.0)  # 累计工时


class WorkloadEstimation(Base):
    """工时估算历史"""
    __tablename__ = "workload_estimations"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement_type = Column(String(20), nullable=False)  # SQLite 兼容
    average_hours = Column(Float, default=0.0)
    sample_count = Column(Integer, default=0)
    updated_at = Column(DateTime, onupdate=func.now())

