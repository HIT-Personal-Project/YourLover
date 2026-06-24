# 校园情感陪伴助手

基于 FastAPI + LangChain + 通义千问 的校园情感陪伴助手Agent服务。

## 功能特性

- **智能对话与陪伴**：支持文字/语音多模态输入，基于人设系统进行个性化对话
- **个性化记忆系统**：记录用户的偏好、经历、重要事件，实现跨会话的长期记忆
- **主动关怀与提醒**：基于用户画像和校园日历，主动发起关怀对话
- **情感引擎**：用户情感识别、AI情感状态管理、情感共鸣

## 技术栈

| 分类 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| LLM框架 | LangChain |
| 大模型 | 通义千问 |
| 语音识别 | Whisper |
| 语音合成 | Edge-TTS |
| 向量数据库 | Chroma |
| 数据库 | SQLite/PostgreSQL |

## 项目结构

```
.
├── app/                    # 应用主包
│   ├── main.py             # FastAPI入口
│   ├── agent/              # Agent模块（核心）
│   │   └── campus_emo_agent.py  # 统一Agent类
│   ├── core/               # 核心配置与工具
│   ├── engine/             # 核心引擎（内部使用）
│   ├── skills/             # 技能插件（内部使用）
│   ├── api/                # API路由
│   ├── models/             # 数据库模型
│   ├── schemas/            # Pydantic模型
│   ├── services/           # 业务服务
│   └── utils/              # 工具函数
├── data/                   # 数据存储
├── tests/                  # 测试
├── requirements.txt        # 依赖声明
└── .env                   # 环境变量
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置环境变量

编辑 `.env` 文件，配置您的 API Key：

```env
LLM_API_KEY=your-qianwen-api-key
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问API文档

启动后访问 http://localhost:8000/docs 查看自动生成的API文档。

## API接口

### 简洁的Agent接口设计

前端只需调用一个接口即可完成所有交互，内部逻辑由Agent自动处理。

| 模块 | 接口 | 功能 | 说明 |
|------|------|------|------|
| 对话 | POST /api/v1/chat/send | 发送消息 | **唯一对外接口** |
| 对话 | GET /api/v1/chat/history | 获取对话历史 | 可选 |
| 对话 | POST /api/v1/chat/reset | 重置会话 | 可选 |

### 接口示例

**发送消息**

请求：
```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-uuid",
    "message": "你好呀"
  }'
```

响应：
```json
{
  "response_id": "uuid-string",
  "user_id": "your-user-uuid",
  "session_id": "session-uuid",
  "message": "你好呀！我是小哈，很高兴认识你~",
  "emotion": {"happy": 0.8},
  "timestamp": "2024-01-01T12:00:00"
}
```

## 核心模块

### 1. Agent类 (CampusEmoAgent)

统一封装所有核心能力的入口类，提供简洁的外部接口：

```python
from app.agent.campus_emo_agent import CampusEmoAgent
from uuid import uuid4

# 创建Agent实例
agent = CampusEmoAgent()

# 配置Agent（可选）
agent.update_config({
    "emotion_enabled": True,
    "memory_enabled": True,
    "skill_enabled": True
})

# 开始对话
user_id = uuid4()
response = agent.chat(user_id, "你好呀")
print(response["message"])
```

### 2. 人设引擎 (Persona Engine)
- 支持大五人格模型
- 可配置语言风格（口头禅、语气词）
- 动态演化随交互积累

### 3. 记忆系统 (Memory System)
- 工作记忆：当前会话上下文
- 短期记忆：最近N轮对话
- 长期记忆：向量数据库存储
- 情景记忆：时间线存储

### 4. 情感引擎 (Emotion Engine)
- 用户情感识别（开心/焦虑/愤怒/孤独）
- AI情感状态机
- 情感共鸣与表情联动

### 5. 主动关怀系统 (Care System)
- 定时关怀
- 事件跟进
- 情绪关怀
- 校园日历联动

## 技能插件

所有技能均由Agent自动匹配调用，无需前端干预：

- DailyGreetingSkill - 日常问候
- EmotionalSupportSkill - 情感支持
- StudyAssistantSkill - 学习助手
- CampusInfoSkill - 校园信息
- MoodTrackerSkill - 心情记录
- DreamInterpreterSkill - 解梦
- JokeTellerSkill - 讲笑话
- MusicRecommendSkill - 推荐音乐

## Agent处理流程

```
前端发送消息 → Agent.chat() → 内部处理管道 → 返回响应
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         情感分析        记忆检索        人设应用
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                         技能匹配
                              │
                              ▼
                         LLM生成响应
                              │
                              ▼
                         记忆存储
```

## Agent配置

```python
config = {
    # 功能开关
    "emotion_enabled": True,      # 启用情感分析
    "memory_enabled": True,       # 启用记忆系统
    "skill_enabled": True,        # 启用技能系统
    "care_enabled": True,         # 启用主动关怀
    
    # 模型配置
    "llm_model": "qwen-plus",
    "emotion_threshold": 0.7,
    
    # 记忆配置
    "memory_top_k": 5,
    "memory_expire_days": 7,
    
    # 技能配置
    "enabled_skills": ["daily_greeting", "emotional_support"]
}

agent = CampusEmoAgent(config)
```

## 开发

```bash
# 运行测试
pytest

# 格式化代码
black .

# 类型检查
mypy app/
```

## 许可证

MIT License
