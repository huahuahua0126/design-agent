"""
LangChain Agent 核心 - 需求采集 Agent
"""
from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
import json
import httpx

from app.core.config import settings


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


class AgentState(BaseModel):
    """Agent 状态"""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    current_form: RequirementFormState = Field(default_factory=RequirementFormState)
    missing_fields: List[str] = Field(default_factory=list)
    design_specs: List[str] = Field(default_factory=list)
    is_complete: bool = False


class RequirementAgent:
    """需求采集 LangChain Agent"""
    
    def __init__(self):
        # 初始化 Qwen API (兼容 OpenAI 格式)
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.7,
            timeout=30,  # 30秒超时，防止卡死
            max_retries=2,  # 最多重试2次
        )
        
        # 构建工作流
        self.workflow = self._build_workflow()
        self.memory = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.memory)
    
    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("extract_requirement", self._extract_requirement)
        workflow.add_node("search_specs", self._search_design_specs)
        workflow.add_node("check_completeness", self._check_completeness)
        workflow.add_node("generate_response", self._generate_response)
        
        # 设置入口
        workflow.set_entry_point("extract_requirement")
        
        # 添加边
        workflow.add_edge("extract_requirement", "search_specs")
        workflow.add_edge("search_specs", "check_completeness")
        workflow.add_edge("check_completeness", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow
    
    async def _extract_requirement(self, state: AgentState) -> AgentState:
        """从用户消息中提取需求字段"""
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        if last_message.get("role") != "user":
            return state
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个需求提取助手。分析用户消息，提取设计需求的结构化字段。

当前需求单状态：
{current_form}

请从用户消息中提取以下字段（如果有的话）：
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
            print(f"Extraction error: {e}")
        
        return state
    
    async def _search_design_specs(self, state: AgentState) -> AgentState:
        """检索设计规范 (RAG)"""
        # 如果有类型，检索相关规范
        if state.current_form.requirement_type:
            # TODO: 实际调用 RAG MCP 服务器
            # 这里先用模拟数据
            specs_map = {
                "banner": [
                    "首页 Banner 建议尺寸：1080x640 或 750x400",
                    "Banner 文字不超过 20 字，主标题字号 48px 以上",
                    "建议使用品牌主色调：#1890FF"
                ],
                "poster": [
                    "海报常用尺寸：A4 (210x297mm) 或 竖版 1080x1920",
                    "海报需要留出安全边距 10mm"
                ],
                "detail_page": [
                    "详情页宽度固定 750px",
                    "首屏需要包含核心卖点"
                ]
            }
            state.design_specs = specs_map.get(state.current_form.requirement_type, [])
        
        return state
    
    async def _check_completeness(self, state: AgentState) -> AgentState:
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
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """生成回复"""
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的设计需求助手，帮助运营人员提交设计需求。

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
    
    async def chat(
        self, 
        user_message: str, 
        conversation_id: str,
        current_form: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """处理用户消息 - 简化版"""
        # 创建新状态（简化：每次都创建新状态，避免复杂的状态恢复）
        state = AgentState()
        
        # 如果传入了当前表单，更新状态
        if current_form:
            try:
                state.current_form = RequirementFormState(**current_form)
            except Exception:
                pass  # 忽略表单解析错误
        
        # 添加用户消息
        state.messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # 运行工作流
            config = {"configurable": {"thread_id": conversation_id}}
            result = await self.app.ainvoke(state, config)
            
            # 处理结果 - result 可能是 dict 或 AgentState
            if isinstance(result, dict):
                messages = result.get("messages", [])
                current_form_data = result.get("current_form", {})
                missing_fields = result.get("missing_fields", [])
                is_complete = result.get("is_complete", False)
                design_specs = result.get("design_specs", [])
                
                # 获取最后一条消息
                response = ""
                if messages and len(messages) > 0:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        response = last_msg.get("content", "")
                    else:
                        response = str(last_msg)
                
                # 处理 current_form
                if isinstance(current_form_data, dict):
                    updated_form = current_form_data
                else:
                    updated_form = current_form_data.model_dump() if hasattr(current_form_data, 'model_dump') else {}
            else:
                # AgentState 对象
                response = result.messages[-1]["content"] if result.messages else ""
                updated_form = result.current_form.model_dump()
                missing_fields = result.missing_fields
                is_complete = result.is_complete
                design_specs = result.design_specs
            
            return {
                "response": response,
                "updated_form": updated_form,
                "missing_fields": missing_fields,
                "is_complete": is_complete,
                "design_specs": design_specs
            }
        except Exception as e:
            print(f"Agent error: {e}")
            # 返回友好的错误消息
            return {
                "response": f"抱歉，处理您的请求时出现了问题。请稍后重试。(错误: {str(e)[:50]})",
                "updated_form": current_form or {},
                "missing_fields": ["title", "requirement_type", "dimensions"],
                "is_complete": False,
                "design_specs": []
            }


# 单例
_agent_instance: Optional[RequirementAgent] = None


def get_requirement_agent() -> RequirementAgent:
    """获取 Agent 单例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RequirementAgent()
    return _agent_instance
