"""
报表统计 API
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement, TaskStatus, TaskTimeLog
from app.models.user import User

router = APIRouter()


# ========== Schemas ==========

class DesignerStats(BaseModel):
    designer_id: int
    designer_name: str
    total_tasks: int
    completed_tasks: int
    total_hours: float
    avg_hours_per_task: float


class DateRangeQuery(BaseModel):
    start_date: date
    end_date: date
    designer_id: Optional[int] = None


# ========== Routes ==========

@router.get("/designer-stats", response_model=List[DesignerStats])
async def get_designer_stats(
    start_date: date,
    end_date: date,
    designer_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取设计师统计数据"""
    # 检查权限
    if current_user.get("role") not in ["admin", "operator"]:
        # 设计师只能查看自己的
        designer_id = int(current_user["sub"])
    
    query = (
        select(
            Requirement.designer_id,
            func.count(Requirement.id).label("total_tasks"),
            func.count(Requirement.id).filter(
                Requirement.status == TaskStatus.COMPLETED
            ).label("completed_tasks")
        )
        .where(Requirement.created_at >= datetime.combine(start_date, datetime.min.time()))
        .where(Requirement.created_at <= datetime.combine(end_date, datetime.max.time()))
        .where(Requirement.designer_id.isnot(None))
        .group_by(Requirement.designer_id)
    )
    
    if designer_id:
        query = query.where(Requirement.designer_id == designer_id)
    
    result = await db.execute(query)
    stats_data = result.all()
    
    # 获取设计师名称和计算工时
    stats = []
    for row in stats_data:
        # 获取设计师信息
        user_result = await db.execute(
            select(User).where(User.id == row.designer_id)
        )
        user = user_result.scalar_one_or_none()
        
        # 计算总工时
        hours_result = await db.execute(
            select(func.sum(TaskTimeLog.accumulated_hours))
            .join(Requirement, TaskTimeLog.requirement_id == Requirement.id)
            .where(Requirement.designer_id == row.designer_id)
            .where(TaskTimeLog.action == "complete")
        )
        total_hours = hours_result.scalar() or 0.0
        
        avg_hours = total_hours / row.completed_tasks if row.completed_tasks > 0 else 0
        
        stats.append(DesignerStats(
            designer_id=row.designer_id,
            designer_name=user.full_name or user.username if user else "Unknown",
            total_tasks=row.total_tasks,
            completed_tasks=row.completed_tasks,
            total_hours=round(total_hours, 2),
            avg_hours_per_task=round(avg_hours, 2)
        ))
    
    return stats


@router.get("/export-excel")
async def export_excel(
    start_date: date,
    end_date: date,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出 Excel 报表"""
    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl 未安装")
    
    # 检查权限
    if current_user.get("role") not in ["admin"]:
        raise HTTPException(status_code=403, detail="只有管理员可以导出报表")
    
    # 获取统计数据
    stats = await get_designer_stats(start_date, end_date, None, current_user, db)
    
    # 创建 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "设计师统计报表"
    
    # 表头
    headers = ["设计师", "总任务数", "已完成", "总工时(小时)", "平均工时"]
    ws.append(headers)
    
    # 数据行
    for stat in stats:
        ws.append([
            stat.designer_name,
            stat.total_tasks,
            stat.completed_tasks,
            stat.total_hours,
            stat.avg_hours_per_task
        ])
    
    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"designer_stats_{start_date}_{end_date}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
