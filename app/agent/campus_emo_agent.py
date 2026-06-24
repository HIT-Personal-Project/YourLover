from uuid import UUID, uuid4
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.engine.persona_engine import PersonaEngine
from app.engine.memory_system import MemorySystem
from app.engine.emotion_engine import EmotionEngine
from app.engine.care_system import CareSystem
from app.skills import skills

class CampusEmoAgent:
    """
    校园情感陪伴助手Agent
    统一封装所有核心能力，提供简洁的外部接口
    
    核心特点：
    - 集中管理：所有Agent逻辑封装在一个类中
    - 灵活配置：通过配置轻松切换功能实现
    - 易于测试：方便进行单元测试和Mock
    - 便于扩展：添加新功能只需修改Agent类
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Agent
        :param config: 配置字典，用于切换不同的功能实现
        """
        self.config = config or {}
        
        # 初始化核心引擎（可通过配置切换实现）
        self.persona_engine = PersonaEngine()
        self.memory_system = MemorySystem()
        self.emotion_engine = EmotionEngine()
        self.care_system = CareSystem()
        
        # 加载技能列表（按优先级排序）
        self.skills = sorted(skills, key=lambda s: s.priority)
        
        # 功能开关状态
        self._emotion_enabled = self.config.get("emotion_enabled", True)
        self._memory_enabled = self.config.get("memory_enabled", True)
        self._skill_enabled = self.config.get("skill_enabled", True)
        self._care_enabled = self.config.get("care_enabled", True)
    
    def chat(self, user_id: UUID, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        核心对话方法 - 前端唯一需要调用的接口
        
        :param user_id: 用户ID
        :param message: 用户消息
        :param session_id: 会话ID（可选）
        :return: 响应字典
        """
        # 1. 情感分析
        emotion_result = self._analyze_emotion(message)
        
        # 2. 记忆检索
        memories = self._retrieve_memory(user_id, message)
        
        # 3. 获取人设
        persona = self._load_persona(user_id)
        
        # 4. 技能匹配
        skill_response = self._match_skill(user_id, message, emotion_result)
        
        # 5. 生成响应
        response_text = self._generate_response(persona, message, skill_response)
        
        # 6. 存储记忆
        self._store_memory(user_id, message)
        
        # 7. 检查主动关怀
        self._check_care(user_id)
        
        return {
            "response_id": str(uuid4()),
            "user_id": str(user_id),
            "session_id": session_id or str(uuid4()),
            "message": response_text,
            "emotion": emotion_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_emotion(self, message: str) -> Dict[str, float]:
        """分析用户情感"""
        if not self._emotion_enabled:
            return {"neutral": 1.0}
        return self.emotion_engine.analyze_emotion(message)
    
    def _retrieve_memory(self, user_id: UUID, query: str, top_k: int = 5) -> list:
        """检索相关记忆"""
        if not self._memory_enabled:
            return []
        return self.memory_system.retrieve_memory(user_id, query, top_k)
    
    def _load_persona(self, user_id: UUID) -> Any:
        """加载用户人设"""
        return self.persona_engine.load_persona(user_id)
    
    def _match_skill(self, user_id: UUID, message: str, emotion: Dict[str, float]) -> Optional[Dict]:
        """匹配技能"""
        if not self._skill_enabled:
            return None
        
        context = {
            "text": message,
            "user_id": user_id,
            "emotion": emotion
        }
        
        for skill in self.skills:
            if skill.can_handle(context):
                return skill.execute(context)
        return None
    
    def _generate_response(self, persona: Any, message: str, skill_response: Optional[Dict]) -> str:
        """生成响应"""
        if skill_response:
            return skill_response.get("response", "")
        return self.persona_engine.generate_response(persona, message)
    
    def _store_memory(self, user_id: UUID, message: str) -> None:
        """存储记忆"""
        if not self._memory_enabled:
            return
        self.memory_system.store_memory(user_id, message, "short")
    
    def _check_care(self, user_id: UUID) -> None:
        """检查主动关怀"""
        if not self._care_enabled:
            return
        self.care_system.check_and_trigger(user_id)
    
    def reset_session(self, user_id: UUID) -> None:
        """重置会话（清除工作记忆）"""
        pass
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置
        
        :param config: 配置字典
        """
        self.config.update(config)
        
        # 更新功能开关
        self._emotion_enabled = self.config.get("emotion_enabled", True)
        self._memory_enabled = self.config.get("memory_enabled", True)
        self._skill_enabled = self.config.get("skill_enabled", True)
        self._care_enabled = self.config.get("care_enabled", True)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def list_skills(self) -> List[str]:
        """列出所有可用技能"""
        return [skill.name for skill in self.skills]
