"""
Agent Tools - 需求管理工具集
"""
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from sqlalchemy import select, and_
from datetime import datetime

from app.models.requirement import Requirement, TaskStatus
from app.core.database import get_db_session
from app.agent.rag_store import get_spec_store


@tool
async def query_requirements(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    查询用户的需求列表
    
    Args:
        user_id: 用户ID
        status: 可选的状态过滤（pending/in_progress/under_review/revising/completed）
        limit: 返回数量限制
    
    Returns:
        需求列表的文本描述
    """
    async with get_db_session() as db:
        query_stmt = select(Requirement).where(Requirement.requester_id == user_id)
        
        if status:
            query_stmt = query_stmt.where(Requirement.status == status)
        
        query_stmt = query_stmt.order_by(Requirement.created_at.desc()).limit(limit)
        
        result = await db.execute(query_stmt)
        requirements = result.scalars().all()
        
        if not requirements:
            return "您还没有提交过需求。"
        
        # 格式化输出
        output = f"找到 {len(requirements)} 条需求：\n\n"
        for req in requirements:
            status_map = {
                "pending": "待接单",
                "in_progress": "进行中",
                "under_review": "待验收",
                "revising": "修改中",
                "completed": "已完成"
            }
            output += f"- [{req.id}] {req.title}\n"
            output += f"  类型：{req.requirement_type}，状态：{status_map.get(req.status, req.status)}\n"
            output += f"  创建时间：{req.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        return output


@tool
async def update_requirement(
    requirement_id: int,
    field: str,
    value: str
) -> str:
    """
    更新需求的指定字段
    
    Args:
        requirement_id: 需求ID
        field: 字段名（title/dimensions/copywriting/additional_notes）
        value: 新值
    
    Returns:
        更新结果描述
    """
    allowed_fields = ["title", "dimensions", "copywriting", "additional_notes"]
    
    if field not in allowed_fields:
        return f"错误：不允许更新字段 {field}。只能更新：{', '.join(allowed_fields)}"
    
    async with get_db_session() as db:
        result = await db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        requirement = result.scalar_one_or_none()
        
        if not requirement:
            return f"错误：未找到ID为 {requirement_id} 的需求。"
        
        # 更新字段
        setattr(requirement, field, value)
        await db.commit()
        
        field_names = {
            "title": "标题",
            "dimensions": "尺寸",
            "copywriting": "文案",
            "additional_notes": "补充说明"
        }
        
        return f"已成功将需求 [{requirement_id}] {requirement.title} 的{field_names[field]}更新为：{value}"


@tool
async def cancel_requirement(
    requirement_id: int,
    reason: str = "用户取消"
) -> str:
    """
    取消需求
    
    Args:
        requirement_id: 需求ID
        reason: 取消原因
    
    Returns:
        取消结果描述
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        requirement = result.scalar_one_or_none()
        
        if not requirement:
            return f"错误：未找到ID为 {requirement_id} 的需求。"
        
        if requirement.status == TaskStatus.COMPLETED.value:
            return f"错误：需求 [{requirement_id}] {requirement.title} 已完成，无法取消。"
        
        # 更新状态和备注
        old_status = requirement.status
        requirement.status = TaskStatus.COMPLETED.value  # 使用completed标记取消
        requirement.additional_notes = (requirement.additional_notes or "") + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 已取消（原因：{reason}）"
        
        await db.commit()
        
        return f"已成功取消需求 [{requirement_id}] {requirement.title}（原状态：{old_status}）"


@tool
async def get_task_status(requirement_id: int) -> str:
    """
    获取任务当前状态和进度
    
    Args:
        requirement_id: 需求ID
    
    Returns:
        任务状态详情
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        requirement = result.scalar_one_or_none()
        
        if not requirement:
            return f"错误：未找到ID为 {requirement_id} 的需求。"
        
        status_map = {
            "pending": "待接单",
            "in_progress": "进行中",
            "under_review": "待验收",
            "revising": "修改中",
            "completed": "已完成"
        }
        
        output = f"需求 [{requirement.id}] {requirement.title}\n\n"
        output += f"当前状态：{status_map.get(requirement.status, requirement.status)}\n"
        output += f"类型：{requirement.requirement_type}\n"
        output += f"尺寸：{requirement.dimensions or '未指定'}\n"
        
        if requirement.designer_id:
            output += f"设计师ID：{requirement.designer_id}\n"
        
        if requirement.deadline:
            output += f"截止时间：{requirement.deadline.strftime('%Y-%m-%d %H:%M')}\n"
        
        output += f"创建时间：{requirement.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if requirement.updated_at:
            output += f"最后更新：{requirement.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        return output


@tool
def search_design_specs(
    query: str,
    requirement_type: Optional[str] = None
) -> str:
    """
    RAG 检索设计规范
    
    Args:
        query: 查询文本（如"Banner 设计有什么规范"）
        requirement_type: 可选的需求类型过滤（banner/poster/detail_page/icon）
    
    Returns:
        相关设计规范文本
    """
    spec_store = get_spec_store()
    
    results = spec_store.search(
        query=query,
        requirement_type=requirement_type,
        k=3
    )
    
    if not results:
        return "未找到相关设计规范。"
    
    output = "查询到以下设计规范：\n\n"
    for i, spec in enumerate(results, 1):
        output += f"【规范 {i}】\n{spec}\n\n"
    
    return output


# 工具列表（供 Agent 使用）
ALL_TOOLS = [
    query_requirements,
    update_requirement,
    cancel_requirement,
    get_task_status,
    search_design_specs
]
