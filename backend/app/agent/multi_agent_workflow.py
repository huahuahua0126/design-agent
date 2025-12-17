"""
Multi-Agent 工作流 - 统一入口
"""
from typing import Dict, Any, Optional
from app.agent.supervisor_agent import get_supervisor_agent
from app.agent.creator_agent import get_creator_agent
from app.agent.query_agent import get_query_agent
from app.agent.manager_agent import get_manager_agent


class MultiAgentOrchestrator:
    """Multi-Agent 编排器"""
    
    def __init__(self):
        self.supervisor = get_supervisor_agent()
        self.creator = get_creator_agent()
        self.query = get_query_agent()
        self.manager = get_manager_agent()
    
    async def process(
        self,
        user_message: str,
        user_id: int,
        current_form: Optional[Dict] = None,
        conversation_history: str = ""
    ) -> Dict[str, Any]:
        """
        处理用户消息 - Multi-Agent 工作流
        
        Args:
            user_message: 用户消息
            user_id: 用户ID
            current_form: 当前表单状态
            conversation_history: 对话历史（用于意图识别）
        
        Returns:
            处理结果
        """
        # 第一步：Supervisor 路由
        target_agent = await self.supervisor.route(
            message=user_message,
            context=conversation_history
        )
        
        # 第二步：调用对应 Agent
        if target_agent == "creator":
            result = await self.creator.process(user_message, current_form)
        elif target_agent == "query":
            result = await self.query.process(user_message, user_id)
        elif target_agent == "manager":
            result = await self.manager.process(user_message)
        else:
            # 默认使用 creator
            result = await self.creator.process(user_message, current_form)
        
        # 添加路由信息（调试用）
        result["routed_to"] = target_agent
        
        return result


# 单例
_orchestrator_instance = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    """获取 Multi-Agent 编排器单例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance
