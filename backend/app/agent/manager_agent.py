"""
Manager Agent - 需求状态管理（简化版）
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.agent.tools import update_requirement, cancel_requirement, get_task_status


class ManagerAgent:
    """管理 Agent - 更新/取消需求"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL,
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.3,
        )
    
    async def process(self, user_message: str) -> Dict[str, Any]:
        """
        处理管理请求
        
        Args:
            user_message: 用户消息
        
        Returns:
            处理结果
        """
        try:
            message_lower = user_message.lower()
            
            # 提取需求ID
            import re
            match = re.search(r'\d+', user_message)
            
            if not match:
                return {
                    "response": "请提供需求ID，例如：取消需求1 或 把需求1的标题改成xxx",
                    "updated_form": {},
                    "missing_fields": [],
                    "is_complete": False,
                    "design_specs": []
                }
            
            req_id = int(match.group())
            
            # 判断操作类型
            if "取消" in user_message:
                result_text = await cancel_requirement.ainvoke({
                    "requirement_id": req_id,
                    "reason": "用户取消"
                })
            
            elif "改" in user_message or "更新" in user_message or "修改" in user_message:
                # 尝试提取字段和值
                if "标题" in user_message:
                    # 提取新标题
                    if "改成" in user_message:
                        new_value = user_message.split("改成")[1].strip('"').strip()
                    elif "为" in user_message:
                        new_value = user_message.split("为")[1].strip('"').strip()
                    else:
                        new_value = "新标题"
                    
                    result_text = await update_requirement.ainvoke({
                        "requirement_id": req_id,
                        "field": "title",
                        "value": new_value
                    })
                
                elif "尺寸" in user_message:
                    match_size = re.search(r'(\d+x\d+|\d+×\d+)', user_message)
                    new_value = match_size.group() if match_size else "1080x640"
                    result_text = await update_requirement.ainvoke({
                        "requirement_id": req_id,
                        "field": "dimensions",
                        "value": new_value
                    })
                
                else:
                    result_text = "目前支持更新：标题、尺寸。例如：把需求1的标题改成xxx"
            
            else:
                result_text = "我可以帮您：\n1. 取消需求（说\"取消需求1\"）\n2. 更新需求（说\"把需求1的标题改成xxx\"）"
            
            return {
                "response": result_text,
                "updated_form": {},
                "missing_fields": [],
                "is_complete": False,
                "design_specs": []
            }
        
        except Exception as e:
            print(f"[Manager] Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": f"抱歉，操作失败：{str(e)[:200]}",
                "updated_form": {},
                "missing_fields": [],
                "is_complete": False,
                "design_specs": []
            }


# 单例
_manager_instance = None


def get_manager_agent() -> ManagerAgent:
    """获取 Manager Agent 单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ManagerAgent()
    return _manager_instance
