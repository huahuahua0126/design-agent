"""
Query Agent - 需求查询 + RAG 检索（简化版）
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.agent.tools import query_requirements, search_design_specs, get_task_status


class QueryAgent:
    """查询 Agent - 需求查询 + 设计规范检索"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.5,
        )
    
    async def process(self, user_message: str, user_id: int) -> Dict[str, Any]:
        """
        处理查询请求
        
        Args:
            user_message: 用户消息
            user_id: 用户ID
        
        Returns:
            查询结果
        """
        try:
            message_lower = user_message.lower()
            
            # 判断查询类型
            if any(keyword in message_lower for keyword in ["规范", "建议", "怎么", "如何"]):
                # RAG 检索设计规范
                specs_text = search_design_specs.invoke({"query": user_message, "requirement_type": None})
                
                prompt = ChatPromptTemplate.from_template(
                    "基于以下设计规范回答用户问题：\n\n{specs}\n\n用户问题：{question}\n\n请简洁、专业地回答："
                )
                response = await self.llm.ainvoke(
                    prompt.format_messages(specs=specs_text, question=user_message)
                )
                result_text = response.content
            
            elif any(keyword in message_lower for keyword in ["需求", "任务", "列表"]):
                # 查询需求列表
                requirements_text = await query_requirements.ainvoke({"user_id": user_id, "status": None, "limit": 10})
                result_text = requirements_text
            
            elif "状态" in message_lower or "进度" in message_lower:
                # 尝试从消息中提取ID
                import re
                match = re.search(r'\d+', user_message)
                if match:
                    req_id = int(match.group())
                    status_text = await get_task_status.ainvoke({"requirement_id": req_id})
                    result_text = status_text
                else:
                    result_text = "请提供需求ID，例如：查询需求1的状态"
            
            else:
                result_text = "您好！我可以帮您：\n1. 查询需求列表（说\"我的需求\"）\n2. 查询设计规范（说\"Banner设计规范\"）\n3. 查询任务状态（说\"需求1的状态\"）"
            
            return {
                "response": result_text,
                "updated_form": {},
                "missing_fields": [],
                "is_complete": False,
                "design_specs": []
            }
        
        except Exception as e:
            print(f"[Query] Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": f"抱歉，查询时出现问题：{str(e)[:200]}",
                "updated_form": {},
                "missing_fields": [],
                "is_complete": False,
                "design_specs": []
            }


# 单例
_query_instance = None


def get_query_agent() -> QueryAgent:
    """获取 Query Agent 单例"""
    global _query_instance
    if _query_instance is None:
        _query_instance = QueryAgent()
    return _query_instance
