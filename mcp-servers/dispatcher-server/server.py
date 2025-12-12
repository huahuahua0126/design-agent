"""
Dispatcher MCP Server - 派单调度工具
"""
import asyncio
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncpg
import os
from datetime import datetime, timedelta

server = Server("dispatcher-mcp")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://design_agent:design_agent_pwd@localhost:5432/design_agent_db")


async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)


@server.tool()
async def get_default_designer(operator_id: int) -> dict:
    """
    获取运营绑定的默认设计师
    
    Args:
        operator_id: 运营用户 ID
    
    Returns:
        默认设计师信息
    """
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow(
            """
            SELECT b.designer_id, u.username, u.full_name
            FROM operator_designer_bindings b
            JOIN users u ON b.designer_id = u.id
            WHERE b.operator_id = $1 AND b.is_active = true
            """,
            operator_id
        )
        if result:
            return {
                "designer_id": result["designer_id"],
                "designer_name": result["full_name"] or result["username"]
            }
        return {"designer_id": None, "message": "未绑定设计师"}
    finally:
        await conn.close()


@server.tool()
async def estimate_workload(
    requirement_type: str,
    complexity: str = "medium"
) -> dict:
    """
    基于历史数据估算工时
    
    Args:
        requirement_type: 设计类型 (banner/poster/detail_page/icon/other)
        complexity: 复杂度 (low/medium/high)
    
    Returns:
        预估工时（小时）
    """
    conn = await get_db_connection()
    try:
        # 查询历史平均工时
        result = await conn.fetchrow(
            """
            SELECT average_hours, sample_count 
            FROM workload_estimations 
            WHERE requirement_type = $1
            """,
            requirement_type
        )
        
        # 复杂度系数
        complexity_factor = {"low": 0.7, "medium": 1.0, "high": 1.5}.get(complexity, 1.0)
        
        if result and result["sample_count"] > 0:
            estimated = result["average_hours"] * complexity_factor
        else:
            # 默认估算
            default_hours = {
                "banner": 2.0,
                "poster": 4.0,
                "detail_page": 8.0,
                "icon": 1.0,
                "other": 3.0
            }
            estimated = default_hours.get(requirement_type, 3.0) * complexity_factor
        
        return {
            "estimated_hours": round(estimated, 1),
            "complexity": complexity,
            "based_on_history": result is not None and result["sample_count"] > 0
        }
    finally:
        await conn.close()


@server.tool()
async def check_designer_availability(
    designer_id: int,
    deadline: str
) -> dict:
    """
    检查设计师在指定时间前的可用性
    
    Args:
        designer_id: 设计师 ID
        deadline: 截止时间 (ISO 格式)
    
    Returns:
        可用性信息
    """
    conn = await get_db_connection()
    try:
        # 统计设计师当前进行中的任务
        result = await conn.fetchrow(
            """
            SELECT COUNT(*) as active_tasks,
                   COALESCE(SUM(estimated_hours), 0) as total_hours
            FROM requirements
            WHERE designer_id = $1 
              AND status IN ('pending', 'in_progress', 'revising')
            """,
            designer_id
        )
        
        active_tasks = result["active_tasks"]
        total_hours = float(result["total_hours"])
        
        # 简单判断可用性
        is_available = active_tasks < 5 and total_hours < 40
        
        return {
            "designer_id": designer_id,
            "active_tasks": active_tasks,
            "estimated_workload_hours": total_hours,
            "is_available": is_available,
            "message": "可接单" if is_available else "工作量较大，建议选择其他设计师"
        }
    finally:
        await conn.close()


@server.tool()
async def suggest_deadline(
    estimated_hours: float,
    designer_id: int
) -> dict:
    """
    根据工时和设计师负载建议截止时间
    
    Args:
        estimated_hours: 预估工时
        designer_id: 设计师 ID
    
    Returns:
        建议的截止时间
    """
    conn = await get_db_connection()
    try:
        # 获取设计师当前工作量
        result = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(estimated_hours), 0) as pending_hours
            FROM requirements
            WHERE designer_id = $1 AND status IN ('pending', 'in_progress')
            """,
            designer_id
        )
        
        pending_hours = float(result["pending_hours"])
        
        # 假设每天工作 8 小时
        total_days = (pending_hours + estimated_hours) / 8
        total_days = max(1, int(total_days) + 1)  # 至少 1 天，向上取整
        
        suggested_deadline = datetime.now() + timedelta(days=total_days)
        
        return {
            "suggested_deadline": suggested_deadline.isoformat(),
            "days_from_now": total_days,
            "pending_hours": pending_hours,
            "message": f"建议 {total_days} 天后交付"
        }
    finally:
        await conn.close()


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
