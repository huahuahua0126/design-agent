"""
Supervisor Agent - 意图识别与路由
"""
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings


class UserIntent(BaseModel):
    """用户意图分类"""
    intent: Literal["create", "query", "manage", "chat"] = Field(
        description="用户意图类型：create=创建需求，query=查询需求/规范，manage=更新/取消需求，chat=闲聊"
    )
    confidence: float = Field(description="置信度 0-1")
    reasoning: str = Field(description="判断理由")


class SupervisorAgent:
    """Supervisor Agent - 路由用户消息到专职 Agent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.3,  # 降低温度提高分类准确性
        )
        
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个意图识别专家。分析用户消息，判断用户的意图。

意图类型：
- create: 用户想创建新的设计需求（如"我需要一个Banner"、"帮我做个海报"）
- query: 用户想查询需求列表、设计规范、任务进度（如"我有哪些需求"、"Banner设计规范是什么"）
- manage: 用户想更新或取消已有需求（如"把标题改成xxx"、"取消这个需求"）
- chat: 闲聊、问候、感谢等（如"你好"、"谢谢"）

请基于用户消息和对话历史上下文判断意图。
"""),
            ("human", """用户消息：{message}

最近的对话上下文：
{context}

请判断用户的意图类型。""")
        ])
    
    async def route(self, message: str, context: str = "") -> str:
        """
        识别用户意图并路由
        
        Args:
            message: 用户消息
            context: 对话上下文
        
        Returns:
            目标 Agent 名称：creator/query/manager/chat
        """
        chain = self.intent_prompt | self.llm.with_structured_output(UserIntent)
        
        try:
            result = await chain.ainvoke({
                "message": message,
                "context": context or "（无上下文）"
            })
            
            # 映射到 Agent 名称
            intent_to_agent = {
                "create": "creator",
                "query": "query",
                "manage": "manager",
                "chat": "creator"  # 闲聊也交给 creator 处理
            }
            
            agent_name = intent_to_agent.get(result.intent, "creator")
            
            print(f"[Supervisor] Intent: {result.intent} (confidence: {result.confidence:.2f}) -> Route to: {agent_name}")
            print(f"[Supervisor] Reasoning: {result.reasoning}")
            
            return agent_name
        
        except Exception as e:
            print(f"[Supervisor] Error: {e}, defaulting to creator")
            return "creator"  # 默认路由到创建 Agent


# 单例
_supervisor_instance = None


def get_supervisor_agent() -> SupervisorAgent:
    """获取 Supervisor Agent 单例"""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = SupervisorAgent()
    return _supervisor_instance
