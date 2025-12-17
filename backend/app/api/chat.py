"""
Agent 对话 API - WebSocket 实时对话
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, List
import json
import uuid

from app.core.database import get_db
from app.core.security import decode_access_token
from app.agent.multi_agent_workflow import get_multi_agent_orchestrator

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    current_form: Optional[Dict] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    updated_form: Dict
    missing_fields: List[str]
    is_complete: bool
    design_specs: List[str]
    conversation_id: str


@router.websocket("/ws/{token}")
async def websocket_chat(websocket: WebSocket, token: str):
    """WebSocket 实时对话"""
    # 验证 token
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    await websocket.accept()
    
    orchestrator = get_multi_agent_orchestrator()
    conversation_id = str(uuid.uuid4())
    is_new_session = True
    conversation_history = []  # Store conversation for context
    user_id = payload.get("user_id", 1)  # Get user_id from token
    
    try:
        # 等待第一条消息，判断是否需要发送欢迎消息
        # 如果客户端发送了 conversation_id，说明是重连，不需要欢迎消息
        data = await websocket.receive_text()
        message_data = json.loads(data)
        
        # 检查是否是 ping 消息或初始化消息
        if message_data.get("type") == "init":
            client_conv_id = message_data.get("conversation_id")
            if client_conv_id:
                conversation_id = client_conv_id
                is_new_session = False
            
            if is_new_session:
                # 发送欢迎消息
                welcome = {
                    "type": "message",
                    "response": "您好！我是设计需求助手。请告诉我您需要什么样的设计？",
                    "updated_form": {},
                    "missing_fields": ["title", "requirement_type", "dimensions"],
                    "is_complete": False,
                    "design_specs": [],
                    "conversation_id": conversation_id
                }
                await websocket.send_json(welcome)
            else:
                # 重连时只发送连接成功消息
                await websocket.send_json({
                    "type": "connected",
                    "conversation_id": conversation_id
                })
        else:
            # 如果不是 init 消息，当作普通消息处理
            user_message = message_data.get("message", "")
            current_form = message_data.get("current_form", {})
            conv_id = message_data.get("conversation_id", conversation_id)
            
            if conv_id and conv_id != conversation_id:
                conversation_id = conv_id
            
            result = await orchestrator.process(
                user_message=user_message,
                user_id=user_id,
                current_form=current_form,
                conversation_history="\n".join(conversation_history[-5:])  # Last 5 messages
            )
            conversation_history.append(f"User: {user_message}")
            conversation_history.append(f"Assistant: {result['response']}")
            
            response = {
                "type": "message",
                "response": result["response"],
                "updated_form": result["updated_form"],
                "missing_fields": result["missing_fields"],
                "is_complete": result["is_complete"],
                "design_specs": result["design_specs"],
                "conversation_id": conversation_id
            }
            await websocket.send_json(response)
        
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message", "")
            current_form = message_data.get("current_form", {})
            conv_id = message_data.get("conversation_id", conversation_id)
            
            # 调用 Multi-Agent Orchestrator
            result = await orchestrator.process(
                user_message=user_message,
                user_id=user_id,
                current_form=current_form,
                conversation_history="\n".join(conversation_history[-5:])
            )
            conversation_history.append(f"User: {user_message}")
            conversation_history.append(f"Assistant: {result['response']}")
            
            # 发送响应
            response = {
                "type": "message",
                "response": result["response"],
                "updated_form": result["updated_form"],
                "missing_fields": result["missing_fields"],
                "is_complete": result["is_complete"],
                "design_specs": result["design_specs"],
                "conversation_id": conv_id
            }
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {conversation_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=4000)


@router.post("/chat", response_model=ChatResponse)
async def http_chat(
    chat_data: ChatMessage,
    db: AsyncSession = Depends(get_db)
):
    """HTTP 对话接口 (备用)"""
    orchestrator = get_multi_agent_orchestrator()
    
    conversation_id = chat_data.conversation_id or str(uuid.uuid4())
    
    # TODO: Get user_id from auth
    result = await orchestrator.process(
        user_message=chat_data.message,
        user_id=1,
        current_form=chat_data.current_form,
        conversation_history=""
    )
    
    return ChatResponse(
        response=result["response"],
        updated_form=result["updated_form"],
        missing_fields=result["missing_fields"],
        is_complete=result["is_complete"],
        design_specs=result["design_specs"],
        conversation_id=conversation_id
    )
