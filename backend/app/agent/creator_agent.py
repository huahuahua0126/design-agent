"""
Creator Agent - 需求创建（基于原 requirement_agent 重构）
"""
from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import json

from app.core.config import settings
from app.agent.rag_store import get_spec_store


class RequirementFormState(BaseModel):
    """需求单状态"""
    title: Optional[str] = None
    requirement_type: Optional[str] = None
    dimensions: Optional[str] = None
    deadline: Optional[str] = None
    copywriting: Optional[str] = None
    reference_images: List[str] = Field(default_factory=list)
    additional_notes: Optional[str] = None
    designer_id: Optional[int] = None
    estimated_hours: Optional[float] = None


class CreatorState(BaseModel):
    """Creator Agent 状态"""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    current_form: RequirementFormState = Field(default_factory=RequirementFormState)
    missing_fields: List[str] = Field(default_factory=list)
    design_specs: List[str] = Field(default_factory=list)
    is_complete: bool = False
    should_cancel: bool = False  # 新增：是否取消


class CreatorAgent:
    """需求创建 Agent - 对话式采集"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.7,
            timeout=30,
            max_retries=2,
        )
        self.spec_store = get_spec_store()
    
    async def _extract_requirement(self, state: CreatorState) -> CreatorState:
        """从用户消息中提取需求字段"""
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        if last_message.get("role") != "user":
            return state
        
        # 检查是否是取消意图
        message_lower = last_message["content"].lower()
        if any(keyword in message_lower for keyword in ["取消", "不做了", "算了"]):
            state.should_cancel = True
            return state
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个需求提取助手。分析用户消息，提取设计需求的结构化字段。

当前需求单状态：
{current_form}

请从用户消息中提取以下字段（如果有）：
- title: 需求标题
- requirement_type: 设计类型 (banner/poster/detail_page/icon/other)
- dimensions: 尺寸 (如 1080x640)
- deadline: 交付时间
- copywriting: 文案内容
- additional_notes: 补充说明

只返回 JSON 格式，只包含需要更新的字段：
{{"title": "...", "requirement_type": "..."}}

如果消息中没有可提取的字段，返回空对象 {{}}
"""),
            ("human", "{user_message}")
        ])
        
        chain = extraction_prompt | self.llm
        
        try:
            result = await chain.ainvoke({
                "current_form": state.current_form.model_dump_json(),
                "user_message": last_message["content"]
            })
            
            # 解析 JSON
            content = result.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            extracted = json.loads(content.strip())
            
            # 更新表单
            for key, value in extracted.items():
                if hasattr(state.current_form, key) and value:
                    setattr(state.current_form, key, value)
        except Exception as e:
            print(f"[Creator] Extraction error: {e}")
        
        return state
    
    async def _search_design_specs(self, state: CreatorState) -> CreatorState:
        """RAG 检索设计规范"""
        if state.current_form.requirement_type and not state.design_specs:
            try:
                specs = self.spec_store.search_by_type(
                    state.current_form.requirement_type,
                    k=3
                )
                state.design_specs = specs
            except Exception as e:
                print(f"[Creator] Spec search error: {e}")
        
        return state
    
    async def _check_completeness(self, state: CreatorState) -> CreatorState:
        """检查必填字段是否完整"""
        required_fields = ["title", "requirement_type", "dimensions"]
        missing = []
        
        for field in required_fields:
            value = getattr(state.current_form, field, None)
            if not value:
                missing.append(field)
        
        state.missing_fields = missing
        state.is_complete = len(missing) == 0
        
        return state
    
    async def _generate_response(self, state: CreatorState) -> CreatorState:
        """生成回复"""
        # 处理取消场景
        if state.should_cancel:
            state.messages.append({
                "role": "assistant",
                "content": "好的，已取消本次需求创建。如需重新开始，请告诉我您的需求。"
            })
            # 重置状态
            state.current_form = RequirementFormState()
            state.missing_fields = ["title", "requirement_type", "dimensions"]
            state.is_complete = False
            state.design_specs = []
            return state
        
        response_prompt = ChatPromptTemplate.from_messages([
            (" system", """你是一个专业的设计需求助手，帮助用户创建设计需求。

当前需求单状态：
{current_form}

设计规范参考：
{design_specs}

缺失的必填字段：{missing_fields}

请根据上述信息生成友好的回复：
1. 如果有设计规范建议，先给出建议
2. 如果有缺失字段，请追问用户
3. 如果需求已完整，告知用户可以提交

语气要专业、友好、简洁。"""),
            MessagesPlaceholder("chat_history"),
            ("human", "{last_message}")
        ])
        
        # 构建聊天历史
        chat_history = []
        for msg in state.messages[:-1]:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            else:
                chat_history.append(AIMessage(content=msg["content"]))
        
        chain = response_prompt | self.llm
        
        last_msg = state.messages[-1]["content"] if state.messages else ""
        
        result = await chain.ainvoke({
            "current_form": state.current_form.model_dump_json(indent=2),
            "design_specs": "\n".join(state.design_specs) if state.design_specs else "暂无",
            "missing_fields": ", ".join(state.missing_fields) if state.missing_fields else "无",
            "chat_history": chat_history,
            "last_message": last_msg
        })
        
        # 添加 AI 回复
        state.messages.append({
            "role": "assistant",
            "content": result.content
        })
        
        return state
    
    async def process(self, user_message: str, current_form: Optional[Dict] = None) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            current_form: 当前表单状态
        
        Returns:
            处理结果
        """
        # 创建状态
        state = CreatorState()
        
        if current_form:
            try:
                state.current_form = RequirementFormState(**current_form)
            except Exception:
                pass
        
        # 添加用户消息
        state.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 执行工作流
        state = await self._extract_requirement(state)
        state = await self._search_design_specs(state)
        state = await self._check_completeness(state)
        state = await self._generate_response(state)
        
        # 返回结果
        response = state.messages[-1]["content"] if state.messages else ""
        updated_form = state.current_form.model_dump()
        
        return {
            "response": response,
            "updated_form": updated_form,
            "missing_fields": state.missing_fields,
            "is_complete": state.is_complete,
            "design_specs": state.design_specs
        }


# 单例
_creator_instance = None


def get_creator_agent() -> CreatorAgent:
    """获取 Creator Agent 单例"""
    global _creator_instance
    if _creator_instance is None:
        _creator_instance = CreatorAgent()
    return _creator_instance
