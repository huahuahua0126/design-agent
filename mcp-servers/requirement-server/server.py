"""
Requirement MCP Server - 需求单管理工具
"""
import asyncio
import json
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncpg
import os

# 创建 MCP Server
server = Server("requirement-mcp")

# 数据库连接
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://design_agent:design_agent_pwd@localhost:5432/design_agent_db")


async def get_db_connection():
    """获取数据库连接"""
    return await asyncpg.connect(DATABASE_URL)


@server.tool()
async def create_requirement(
    title: str,
    requirement_type: str = "other",
    dimensions: Optional[str] = None,
    copywriting: Optional[str] = None,
    requester_id: Optional[int] = None,
    designer_id: Optional[int] = None
) -> dict:
    """
    创建新的需求单
    
    Args:
        title: 需求标题
        requirement_type: 设计类型 (banner/poster/detail_page/icon/other)
        dimensions: 尺寸 (如 1080x640)
        copywriting: 文案内容
        requester_id: 需求方用户 ID
        designer_id: 设计师用户 ID
    
    Returns:
        创建的需求单信息
    """
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow(
            """
            INSERT INTO requirements (title, requirement_type, dimensions, copywriting, 
                                       requester_id, designer_id, status, reference_images)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', '[]')
            RETURNING id, title, requirement_type, status, created_at
            """,
            title, requirement_type, dimensions, copywriting, requester_id, designer_id
        )
        return {
            "success": True,
            "requirement_id": result["id"],
            "title": result["title"],
            "status": result["status"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await conn.close()


@server.tool()
async def update_requirement(
    requirement_id: int,
    title: Optional[str] = None,
    requirement_type: Optional[str] = None,
    dimensions: Optional[str] = None,
    copywriting: Optional[str] = None,
    deadline: Optional[str] = None,
    designer_id: Optional[int] = None
) -> dict:
    """
    更新需求单字段
    
    Args:
        requirement_id: 需求单 ID
        title: 需求标题
        requirement_type: 设计类型
        dimensions: 尺寸
        copywriting: 文案内容
        deadline: 截止时间
        designer_id: 设计师 ID
    
    Returns:
        更新结果
    """
    conn = await get_db_connection()
    try:
        # 构建动态更新语句
        updates = []
        values = []
        param_idx = 1
        
        if title:
            updates.append(f"title = ${param_idx}")
            values.append(title)
            param_idx += 1
        if requirement_type:
            updates.append(f"requirement_type = ${param_idx}")
            values.append(requirement_type)
            param_idx += 1
        if dimensions:
            updates.append(f"dimensions = ${param_idx}")
            values.append(dimensions)
            param_idx += 1
        if copywriting:
            updates.append(f"copywriting = ${param_idx}")
            values.append(copywriting)
            param_idx += 1
        if deadline:
            updates.append(f"deadline = ${param_idx}")
            values.append(deadline)
            param_idx += 1
        if designer_id:
            updates.append(f"designer_id = ${param_idx}")
            values.append(designer_id)
            param_idx += 1
        
        if not updates:
            return {"success": False, "error": "No fields to update"}
        
        values.append(requirement_id)
        query = f"""
            UPDATE requirements 
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = ${param_idx}
            RETURNING id, title, status
        """
        
        result = await conn.fetchrow(query, *values)
        return {
            "success": True,
            "requirement_id": result["id"],
            "message": "需求单已更新"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        await conn.close()


@server.tool()
async def get_requirement(requirement_id: int) -> dict:
    """
    获取需求单详情
    
    Args:
        requirement_id: 需求单 ID
    
    Returns:
        需求单详细信息
    """
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow(
            """
            SELECT id, title, requirement_type, dimensions, deadline, 
                   copywriting, reference_images, additional_notes,
                   requester_id, designer_id, estimated_hours, status,
                   created_at, updated_at
            FROM requirements WHERE id = $1
            """,
            requirement_id
        )
        if result:
            return dict(result)
        return {"error": "需求单不存在"}
    finally:
        await conn.close()


@server.tool()
async def validate_requirement(requirement_id: int) -> dict:
    """
    校验需求单必填字段，返回缺失项
    
    Args:
        requirement_id: 需求单 ID
    
    Returns:
        校验结果和缺失字段列表
    """
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow(
            "SELECT title, requirement_type, dimensions FROM requirements WHERE id = $1",
            requirement_id
        )
        if not result:
            return {"valid": False, "error": "需求单不存在"}
        
        missing = []
        if not result["title"]:
            missing.append("title")
        if not result["requirement_type"]:
            missing.append("requirement_type")
        if not result["dimensions"]:
            missing.append("dimensions")
        
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing
        }
    finally:
        await conn.close()


async def main():
    """运行 MCP 服务器"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
