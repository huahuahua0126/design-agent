"""
任务管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement, TaskStatus, TaskTimeLog

router = APIRouter()


# ========== Schemas ==========

class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskTimeLogResponse(BaseModel):
    id: int
    requirement_id: int
    action: str
    timestamp: datetime
    accumulated_hours: float

    class Config:
        from_attributes = True


# ========== Routes ==========

@router.post("/{requirement_id}/start")
async def start_task(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """开始制作 - 设计师点击"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    if requirement.status != TaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能从待接单状态开始")
    
    # 更新状态
    requirement.status = TaskStatus.IN_PROGRESS
    
    # 记录时间
    time_log = TaskTimeLog(
        requirement_id=requirement_id,
        action="start",
        accumulated_hours=0.0
    )
    db.add(time_log)
    
    await db.commit()
    
    return {"message": "已开始制作", "status": TaskStatus.IN_PROGRESS}


@router.post("/{requirement_id}/submit-review")
async def submit_for_review(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交验收 - 设计师点击"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    if requirement.status not in [TaskStatus.IN_PROGRESS, TaskStatus.REVISING]:
        raise HTTPException(status_code=400, detail="只能从进行中或修改中状态提交")
    
    # 计算累计工时
    result = await db.execute(
        select(TaskTimeLog)
        .where(TaskTimeLog.requirement_id == requirement_id)
        .order_by(TaskTimeLog.timestamp.desc())
    )
    last_log = result.scalars().first()
    
    # 更新状态
    requirement.status = TaskStatus.UNDER_REVIEW
    
    # 记录时间
    accumulated = _calculate_accumulated_hours(last_log)
    time_log = TaskTimeLog(
        requirement_id=requirement_id,
        action="pause",
        accumulated_hours=accumulated
    )
    db.add(time_log)
    
    await db.commit()
    
    return {"message": "已提交验收", "status": TaskStatus.UNDER_REVIEW}


@router.post("/{requirement_id}/request-revision")
async def request_revision(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """需要修改 - 运营点击"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    if requirement.status != TaskStatus.UNDER_REVIEW:
        raise HTTPException(status_code=400, detail="只能从待验收状态发起修改")
    
    requirement.status = TaskStatus.REVISING
    
    time_log = TaskTimeLog(
        requirement_id=requirement_id,
        action="resume"
    )
    db.add(time_log)
    
    await db.commit()
    
    return {"message": "已发起修改", "status": TaskStatus.REVISING}


@router.post("/{requirement_id}/complete")
async def complete_task(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """完成任务"""
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()
    
    if not requirement:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    if requirement.status != TaskStatus.UNDER_REVIEW:
        raise HTTPException(status_code=400, detail="只能从待验收状态完成")
    
    requirement.status = TaskStatus.COMPLETED
    
    time_log = TaskTimeLog(
        requirement_id=requirement_id,
        action="complete"
    )
    db.add(time_log)
    
    await db.commit()
    
    return {"message": "任务已完成", "status": TaskStatus.COMPLETED}


@router.get("/{requirement_id}/time-logs", response_model=List[TaskTimeLogResponse])
async def get_time_logs(
    requirement_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务时间记录"""
    result = await db.execute(
        select(TaskTimeLog)
        .where(TaskTimeLog.requirement_id == requirement_id)
        .order_by(TaskTimeLog.timestamp)
    )
    
    return result.scalars().all()


def _calculate_accumulated_hours(last_log: Optional[TaskTimeLog]) -> float:
    """计算累计工时"""
    if not last_log:
        return 0.0
    
    # 简化计算：从最后一次 start/resume 到现在的时间
    now = datetime.utcnow()
    if last_log.action in ["start", "resume"]:
        diff = now - last_log.timestamp.replace(tzinfo=None)
        return last_log.accumulated_hours + diff.total_seconds() / 3600
    
    return last_log.accumulated_hours
