"""
Analytics MCP Server - 统计分析工具
"""
import asyncio
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncpg
import os
from datetime import date

server = Server("analytics-mcp")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://design_agent:design_agent_pwd@localhost:5432/design_agent_db")


async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)


@server.tool()
async def get_designer_stats(
    designer_id: int,
    start_date: str,
    end_date: str
) -> dict:
    """
    获取设计师统计数据
    
    Args:
        designer_id: 设计师 ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        统计数据
    """
    conn = await get_db_connection()
    try:
        # 任务统计
        task_stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks
            FROM requirements
            WHERE designer_id = $1
              AND created_at >= $2
              AND created_at <= $3
            """,
            designer_id, start_date, end_date
        )
        
        # 工时统计
        hours_result = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(t.accumulated_hours), 0) as total_hours
            FROM task_time_logs t
            JOIN requirements r ON t.requirement_id = r.id
            WHERE r.designer_id = $1
              AND t.action = 'complete'
              AND r.created_at >= $2
              AND r.created_at <= $3
            """,
            designer_id, start_date, end_date
        )
        
        total_tasks = task_stats["total_tasks"]
        completed_tasks = task_stats["completed_tasks"]
        total_hours = float(hours_result["total_hours"])
        
        return {
            "designer_id": designer_id,
            "period": {"start": start_date, "end": end_date},
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "total_hours": round(total_hours, 2),
            "avg_hours_per_task": round(total_hours / completed_tasks, 2) if completed_tasks > 0 else 0,
            "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
        }
    finally:
        await conn.close()


@server.tool()
async def get_team_summary(
    start_date: str,
    end_date: str
) -> dict:
    """
    获取团队整体统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        团队统计数据
    """
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                COUNT(DISTINCT designer_id) as active_designers,
                COUNT(DISTINCT requester_id) as active_operators
            FROM requirements
            WHERE created_at >= $1 AND created_at <= $2
            """,
            start_date, end_date
        )
        
        return {
            "period": {"start": start_date, "end": end_date},
            "total_tasks": result["total_tasks"],
            "completed_tasks": result["completed_tasks"],
            "active_designers": result["active_designers"],
            "active_operators": result["active_operators"],
            "completion_rate": round(result["completed_tasks"] / result["total_tasks"] * 100, 1) if result["total_tasks"] > 0 else 0
        }
    finally:
        await conn.close()


@server.tool()
async def get_requirement_type_distribution(
    start_date: str,
    end_date: str
) -> list:
    """
    获取需求类型分布
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        各类型需求数量
    """
    conn = await get_db_connection()
    try:
        results = await conn.fetch(
            """
            SELECT requirement_type, COUNT(*) as count
            FROM requirements
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY requirement_type
            ORDER BY count DESC
            """,
            start_date, end_date
        )
        
        return [{"type": r["requirement_type"], "count": r["count"]} for r in results]
    finally:
        await conn.close()


@server.tool()
async def update_workload_estimation(
    requirement_type: str,
    actual_hours: float
) -> dict:
    """
    更新工时估算模型（完成任务后调用）
    
    Args:
        requirement_type: 需求类型
        actual_hours: 实际耗时
    
    Returns:
        更新结果
    """
    conn = await get_db_connection()
    try:
        # 获取当前估算
        current = await conn.fetchrow(
            "SELECT average_hours, sample_count FROM workload_estimations WHERE requirement_type = $1",
            requirement_type
        )
        
        if current:
            # 更新移动平均
            new_count = current["sample_count"] + 1
            new_avg = (current["average_hours"] * current["sample_count"] + actual_hours) / new_count
            
            await conn.execute(
                """
                UPDATE workload_estimations 
                SET average_hours = $1, sample_count = $2, updated_at = NOW()
                WHERE requirement_type = $3
                """,
                new_avg, new_count, requirement_type
            )
        else:
            # 插入新记录
            await conn.execute(
                """
                INSERT INTO workload_estimations (requirement_type, average_hours, sample_count)
                VALUES ($1, $2, 1)
                """,
                requirement_type, actual_hours
            )
        
        return {"success": True, "message": "工时估算模型已更新"}
    finally:
        await conn.close()


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
