from fastapi import APIRouter
from uuid import UUID
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.campus_emo_agent import CampusEmoAgent

router = APIRouter()

# 全局Agent实例
agent = CampusEmoAgent()

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送消息 - Agent核心入口
    
    前端唯一需要调用的接口，内部自动处理所有逻辑：
    - 情感分析
    - 记忆检索
    - 人设应用
    - 技能匹配
    - LLM生成响应
    - 记忆存储
    """
    result = agent.chat(
        user_id=request.user_id,
        message=request.message,
        session_id=str(request.session_id) if request.session_id else None
    )
    
    return ChatResponse(**result)

@router.get("/history")
async def get_chat_history(user_id: UUID, session_id: UUID = None):
    """获取对话历史"""
    return {"message": "获取对话历史", "user_id": user_id, "session_id": session_id}

@router.post("/reset")
async def reset_session(user_id: UUID):
    """重置会话（清除工作记忆）"""
    agent.reset_session(user_id)
    return {"message": "会话已重置", "user_id": user_id}
