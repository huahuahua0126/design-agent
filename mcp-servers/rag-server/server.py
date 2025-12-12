"""
RAG MCP Server - 设计规范检索工具
"""
import asyncio
from typing import Optional, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
import chromadb
from chromadb.config import Settings
import os
import httpx

server = Server("rag-mcp")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# ChromaDB 客户端
chroma_client = None
collection = None


def get_chroma_client():
    global chroma_client, collection
    if chroma_client is None:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # 获取或创建集合
        collection = chroma_client.get_or_create_collection(
            name="design_specs",
            metadata={"description": "设计规范知识库"}
        )
    return collection


async def get_embedding(text: str) -> List[float]:
    """使用 Qwen API 获取文本向量"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "text-embedding-v3",
                "input": text
            }
        )
        data = response.json()
        return data["data"][0]["embedding"]


@server.tool()
async def search_design_specs(
    query: str,
    requirement_type: Optional[str] = None,
    top_k: int = 5
) -> List[dict]:
    """
    检索相关的设计规范和历史案例
    
    Args:
        query: 搜索查询
        requirement_type: 设计类型过滤 (可选)
        top_k: 返回结果数量
    
    Returns:
        相关规范列表，包含内容和来源
    """
    try:
        col = get_chroma_client()
        
        # 构建过滤条件
        where_filter = None
        if requirement_type:
            where_filter = {"requirement_type": requirement_type}
        
        # 查询
        results = col.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )
        
        # 格式化结果
        specs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                specs.append({
                    "content": doc,
                    "source": metadata.get("source", "设计规范"),
                    "requirement_type": metadata.get("requirement_type", ""),
                    "relevance_score": 1 - (results["distances"][0][i] if results["distances"] else 0)
                })
        
        return specs if specs else _get_default_specs(requirement_type)
    except Exception as e:
        # 如果 ChromaDB 连接失败，返回默认规范
        print(f"RAG error: {e}")
        return _get_default_specs(requirement_type)


def _get_default_specs(requirement_type: Optional[str]) -> List[dict]:
    """返回默认设计规范"""
    default_specs = {
        "banner": [
            {"content": "首页 Banner 建议尺寸：1080x640 或 750x400", "source": "设计规范 v2.0"},
            {"content": "Banner 文字不超过 20 字，主标题字号 48px 以上", "source": "设计规范 v2.0"},
            {"content": "建议使用品牌主色调，对比度需满足 WCAG AA 标准", "source": "设计规范 v2.0"},
        ],
        "poster": [
            {"content": "海报常用尺寸：A4 (210x297mm) 或 竖版 1080x1920", "source": "设计规范 v2.0"},
            {"content": "海报需要留出安全边距 10mm", "source": "设计规范 v2.0"},
            {"content": "重要信息放置在视觉中心位置", "source": "设计规范 v2.0"},
        ],
        "detail_page": [
            {"content": "详情页宽度固定 750px", "source": "设计规范 v2.0"},
            {"content": "首屏需要包含核心卖点，高度不超过 1200px", "source": "设计规范 v2.0"},
            {"content": "图片需压缩，单张不超过 200KB", "source": "设计规范 v2.0"},
        ],
        "icon": [
            {"content": "图标常用尺寸：24x24、48x48、96x96", "source": "设计规范 v2.0"},
            {"content": "图标需要保持视觉一致性，线宽统一", "source": "设计规范 v2.0"},
        ]
    }
    
    if requirement_type and requirement_type in default_specs:
        return default_specs[requirement_type]
    
    # 返回通用规范
    return [
        {"content": "所有设计稿需要标注尺寸和间距", "source": "设计规范 v2.0"},
        {"content": "使用品牌规定的色彩体系", "source": "设计规范 v2.0"},
        {"content": "字体优先使用思源黑体或品牌指定字体", "source": "设计规范 v2.0"},
    ]


@server.tool()
async def add_design_spec(
    content: str,
    source: str,
    requirement_type: Optional[str] = None
) -> dict:
    """
    添加设计规范到知识库
    
    Args:
        content: 规范内容
        source: 来源 (如文档名称)
        requirement_type: 适用的设计类型
    
    Returns:
        添加结果
    """
    try:
        col = get_chroma_client()
        
        # 生成 ID
        import hashlib
        doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
        
        metadata = {"source": source}
        if requirement_type:
            metadata["requirement_type"] = requirement_type
        
        col.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return {"success": True, "doc_id": doc_id, "message": "规范已添加"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.tool()
async def ingest_document(
    file_path: str,
    doc_type: str = "markdown"
) -> dict:
    """
    导入设计规范文档到知识库
    
    Args:
        file_path: 文档路径
        doc_type: 文档类型 (markdown/text)
    
    Returns:
        导入结果
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 简单分段
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        col = get_chroma_client()
        
        added = 0
        for i, para in enumerate(paragraphs):
            if len(para) > 20:  # 过滤太短的段落
                import hashlib
                doc_id = hashlib.md5(f"{file_path}_{i}_{para}".encode()).hexdigest()[:16]
                col.add(
                    documents=[para],
                    metadatas=[{"source": file_path}],
                    ids=[doc_id]
                )
                added += 1
        
        return {"success": True, "added_count": added, "message": f"已导入 {added} 条规范"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
