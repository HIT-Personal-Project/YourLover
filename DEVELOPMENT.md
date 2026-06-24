# 校园情感陪伴助手 - 开发文档

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [核心模块设计](#3-核心模块设计)
4. [API接口设计](#4-api接口设计)
5. [数据库设计](#5-数据库设计)
6. [技术选型](#6-技术选型)
7. [部署与运行](#7-部署与运行)
8. [安全与性能](#8-安全与性能)

---

## 1. 项目概述

### 1.1 项目定位

校园情感陪伴助手是一款面向高校学生的AI情感陪伴应用，旨在通过智能对话、个性化记忆和主动关怀，为学生提供温暖、贴心的情感支持。

### 1.2 核心功能

| 功能模块 | 功能描述 |
|----------|----------|
| 智能对话与陪伴 | 支持文字/语音多模态输入，基于人设系统进行个性化对话 |
| 个性化记忆系统 | 记录用户的偏好、经历、重要事件，实现跨会话的长期记忆 |
| 主动关怀与提醒 | 基于用户画像和校园日历，主动发起关怀对话 |
| 情感引擎 | 用户情感识别、AI情感状态管理、情感共鸣 |

### 1.3 创新点

1. **长短期记忆**：分层记忆系统，支持工作记忆、短期记忆、长期记忆、情景记忆
2. **语言风格**：可配置的人设系统，支持口头禅、语气词、表达习惯
3. **情感共鸣**：AI具有自己的情感状态，能感知并回应用户情绪

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        交互层 (Interaction)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │对话管理  │ │意图识别  │ │槽位填充  │ │多轮状态机│ │中断处理  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────┬─────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        智能层 (Intelligence)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │人设引擎  │ │记忆系统  │ │情感引擎  │ │用户画像  │ │推理决策  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────┬─────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        能力层 (Capability)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │技能插件  │ │工具调用  │ │知识检索  │ │外部API  │ │多模态    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└───────────────────────┬─────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据层 (Data)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │对话日志  │ │记忆存储  │ │用户画像  │ │配置管理  │ │知识库    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 项目目录结构

```
.
├── app/                                    # 应用主包
│   ├── __init__.py                         # 应用初始化
│   ├── main.py                             # FastAPI入口文件
│   ├── core/                               # 核心配置与工具
│   │   ├── __init__.py
│   │   ├── config.py                       # 配置管理
│   │   ├── logging.py                      # 日志配置
│   │   └── dependencies.py                 # 依赖注入
│   ├── engine/                             # 核心引擎模块
│   │   ├── __init__.py
│   │   ├── persona_engine.py               # 人设引擎
│   │   ├── memory_system.py                # 记忆系统
│   │   ├── emotion_engine.py               # 情感引擎
│   │   └── care_system.py                  # 主动关怀系统
│   ├── skills/                             # 技能插件系统
│   │   ├── __init__.py
│   │   ├── base_skill.py                   # 技能基类
│   │   ├── daily_greeting.py               # 日常问候
│   │   ├── emotional_support.py            # 情感支持
│   │   ├── study_assistant.py              # 学习助手
│   │   ├── campus_info.py                  # 校园信息
│   │   ├── mood_tracker.py                 # 心情记录
│   │   ├── joke_teller.py                  # 讲笑话
│   │   └── music_recommend.py              # 推荐音乐
│   ├── api/                                # API路由
│   │   ├── __init__.py
│   │   └── v1/                             # API v1版本
│   │       ├── __init__.py
│   │       ├── chat.py                     # 对话接口
│   │       ├── memory.py                   # 记忆管理接口
│   │       ├── persona.py                  # 人设管理接口
│   │       ├── emotion.py                  # 情感相关接口
│   │       └── care.py                     # 关怀系统接口
│   ├── models/                             # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py                         # 用户模型
│   │   ├── persona.py                      # 人设模型
│   │   ├── memory.py                       # 记忆模型
│   │   ├── conversation.py                 # 对话记录模型
│   │   └── care_event.py                   # 关怀事件模型
│   ├── schemas/                            # Pydantic数据模型
│   │   ├── __init__.py
│   │   ├── chat.py                         # 对话相关Schema
│   │   ├── persona.py                      # 人设Schema
│   │   ├── memory.py                       # 记忆Schema
│   │   ├── emotion.py                      # 情感Schema
│   │   └── care.py                         # 关怀Schema
│   ├── services/                           # 业务服务层
│   │   ├── __init__.py
│   │   ├── llm_service.py                  # LLM服务
│   │   ├── voice_service.py                # 语音服务
│   │   ├── vector_db_service.py            # 向量数据库服务
│   │   └── calendar_service.py             # 日历服务
│   └── utils/                              # 工具函数
│       ├── __init__.py
│       ├── text_utils.py                   # 文本处理工具
│       └── time_utils.py                   # 时间工具
├── data/                                   # 数据存储目录
│   ├── chroma/                             # Chroma向量数据库
│   └── sqlite/                             # SQLite数据库
├── tests/                                  # 测试目录
├── requirements.txt                        # 依赖声明
├── .env                                    # 环境变量配置
└── README.md                               # 项目说明文档
```

---

## 3. 核心模块设计

### 3.1 人设系统（Persona Engine）

**设计目标**：实现可配置的AI人设，支持性格维度、语言风格、兴趣爱好，并支持动态演化。

**数据模型**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 关联用户ID |
| name | str | AI名字 |
| age | int | AI年龄 |
| identity | str | AI身份 |
| backstory | str | 背景故事 |
| personality | JSON | 大五人格维度 |
| speaking_style | JSON | 语言风格配置 |
| interests | List[str] | 兴趣爱好 |
| evolution_rate | float | 动态演化速率 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

**核心接口**：

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| load_persona | 加载用户的人设配置 | user_id: UUID | Persona |
| generate_response | 根据人设生成响应 | persona: Persona, prompt: str | str |
| update_persona | 更新人设配置 | user_id: UUID, updates: dict | Persona |
| evolve_persona | 根据交互演化人设 | user_id: UUID, interaction: str | None |

**人设JSON示例**：

```json
{
  "name": "小哈",
  "age": 20,
  "identity": "哈工大AI助教",
  "backstory": "热爱学习，喜欢讲冷笑话",
  "personality": {
    "openness": 0.8,
    "conscientiousness": 0.7,
    "extraversion": 0.6,
    "agreeableness": 0.8,
    "neuroticism": 0.3
  },
  "speaking_style": {
    "catchphrases": ["哎呀~", "让我想想...", "有意思!"],
    "tone": "friendly_playful",
    "sentence_endings": ["呢~", "哦~", "呀~"]
  },
  "interests": ["学习", "科技", "冷笑话"],
  "evolution_rate": 0.1
}
```

### 3.2 记忆系统（Memory System）

**设计目标**：实现长短期记忆分层存储，支持记忆的提取、存储、触发与召回。

**记忆类型分层**：

| 类型 | 存储方式 | 用途 | 有效期 |
|------|----------|------|--------|
| 工作记忆 | 当前会话内存 | 当前对话上下文 | 会话结束后清除 |
| 短期记忆 | SQLite | 最近N轮对话摘要 | 7天 |
| 长期记忆 | Chroma向量数据库 | 用户重要事实、喜好、经历 | 永久 |
| 情景记忆 | SQLite时间线 | 特定事件回顾 | 永久 |

**核心接口**：

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| store_memory | 存储记忆 | user_id, content, memory_type, metadata | None |
| retrieve_memory | 检索相关记忆 | user_id, query, top_k | List[Memory] |
| get_recent_memory | 获取最近记忆 | user_id, limit | List[Memory] |
| update_memory | 更新记忆内容 | memory_id, content | None |
| delete_memory | 删除记忆 | memory_id | None |
| extract_important_info | 从对话中提取重要信息 | conversation | List[str] |

### 3.3 情感引擎（Emotion Engine）

**设计目标**：实现用户情感识别、AI情感状态管理、情感共鸣与表情联动。

**情感识别流程**：

```
用户输入 → 文本/语音分析 → 情感识别 → AI情感状态更新 → 情感表达生成
```

**情感类型定义**：

| 情感类型 | 说明 | 强度范围 |
|----------|------|----------|
| happy | 开心 | 0-100 |
| sad | 难过 | 0-100 |
| anxious | 焦虑 | 0-100 |
| angry | 愤怒 | 0-100 |
| lonely | 孤独 | 0-100 |
| neutral | 中性 | 默认 |

**核心接口**：

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| analyze_emotion | 分析文本情感 | text: str | Dict[str, float] |
| analyze_speech_emotion | 分析语音情感 | audio_data: bytes | Dict[str, float] |
| update_ai_emotion | 更新AI情感状态 | user_id, user_emotion | Dict[str, float] |
| generate_emotional_response | 生成情感化响应 | user_id, prompt | str |
| get_emotion_state | 获取当前情感状态 | user_id | Dict[str, float] |

### 3.4 主动关怀系统（Care System）

**设计目标**：基于用户画像和校园日历，实现定时关怀、事件跟进、情绪关怀与校园日历联动。

**关怀类型**：

| 类型 | 说明 | 触发条件 |
|------|------|----------|
| 定时关怀 | 早安、晚安等定时问候 | 时间触发 |
| 事件跟进 | 跟进用户提到的重要事件 | 时间/事件触发 |
| 情绪关怀 | 检测到用户情绪低落时主动安慰 | 情绪检测触发 |
| 校园日历联动 | 考试周、节假日等特殊时期关怀 | 日历事件触发 |

**核心接口**：

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| schedule_care_event | 创建关怀事件 | user_id, care_type, content, trigger_time, repeat_type | CareEvent |
| execute_care_event | 执行关怀事件 | event_id | None |
| check_and_trigger | 检查并触发到期的关怀事件 | user_id | List[CareEvent] |
| detect_and_care | 检测情绪并触发关怀 | user_id, user_emotion | bool |
| sync_campus_calendar | 同步校园日历事件 | user_id | None |
| list_care_events | 列出关怀事件 | user_id, status | List[CareEvent] |

### 3.5 技能系统（Skill System）

**设计目标**：实现可插拔的技能插件架构，支持动态扩展功能。

**技能基类设计**：

```python
class BaseSkill:
    name: str                     # 技能名称
    trigger: List[str]            # 触发关键词/意图
    priority: int                 # 优先级（数值越小优先级越高）
    
    def can_handle(self, context: dict) -> bool:
        """判断是否能处理当前上下文"""
        pass
    
    def execute(self, context: dict) -> dict:
        """执行技能逻辑"""
        pass
```

**内置技能列表**：

| 技能名称 | 触发关键词 | 功能说明 |
|----------|------------|----------|
| DailyGreetingSkill | "早安", "晚安", "早上好" | 日常问候 |
| EmotionalSupportSkill | "难过", "伤心", "心情不好" | 情感支持 |
| StudyAssistantSkill | "学习", "作业", "考试" | 学习助手 |
| CampusInfoSkill | "课表", "食堂", "图书馆" | 校园信息 |
| MoodTrackerSkill | "记录心情", "今天心情" | 心情记录 |
| DreamInterpreterSkill | "解梦", "梦见" | 解梦（趣味） |
| JokeTellerSkill | "笑话", "开心一下" | 讲笑话 |
| MusicRecommendSkill | "推荐音乐", "想听音乐" | 推荐音乐 |

---

## 4. API接口设计

### 4.1 对话接口

| API路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/chat/send` | POST | 发送消息 |
| `/api/v1/chat/history` | GET | 获取对话历史 |
| `/api/v1/chat/session` | POST | 创建新会话 |
| `/api/v1/chat/session/{session_id}` | DELETE | 结束会话 |

**POST /api/v1/chat/send**

请求体：
```json
{
  "user_id": "uuid-string",
  "message": "你好呀~",
  "message_type": "text",
  "voice_data": "base64-encoded-audio",
  "session_id": "uuid-string"
}
```

响应体：
```json
{
  "response_id": "uuid-string",
  "user_id": "uuid-string",
  "session_id": "uuid-string",
  "message": "你好呀！我是小哈，很高兴认识你~",
  "message_type": "text",
  "voice_data": "base64-encoded-audio",
  "emotion": {"happy": 0.8},
  "timestamp": "2024-01-01 12:00:00"
}
```

### 4.2 记忆管理接口

| API路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/memory` | GET | 获取用户记忆列表 |
| `/api/v1/memory` | POST | 创建记忆 |
| `/api/v1/memory/{memory_id}` | GET | 获取单个记忆 |
| `/api/v1/memory/{memory_id}` | PUT | 更新记忆 |
| `/api/v1/memory/{memory_id}` | DELETE | 删除记忆 |
| `/api/v1/memory/search` | POST | 搜索记忆 |

### 4.3 人设管理接口

| API路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/persona` | GET | 获取用户人设 |
| `/api/v1/persona` | POST | 创建/更新人设 |
| `/api/v1/persona/evolve` | POST | 触发人设演化 |

### 4.4 情感接口

| API路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/emotion/analyze` | POST | 分析情感 |
| `/api/v1/emotion/state` | GET | 获取情感状态 |

### 4.5 关怀系统接口

| API路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/care/events` | GET | 获取关怀事件列表 |
| `/api/v1/care/events` | POST | 创建关怀事件 |
| `/api/v1/care/events/{event_id}` | DELETE | 删除关怀事件 |
| `/api/v1/care/calendar/sync` | POST | 同步校园日历 |

---

## 5. 数据库设计

### 5.1 用户表（users）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 用户唯一标识 |
| username | VARCHAR(50) | UNIQUE NOT NULL | 用户名 |
| nickname | VARCHAR(50) | | 用户昵称 |
| avatar | VARCHAR(255) | | 头像URL |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

### 5.2 会话表（conversations）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 会话ID |
| user_id | UUID | FOREIGN KEY | 用户ID |
| title | VARCHAR(100) | | 会话标题 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

### 5.3 消息表（messages）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 消息ID |
| conversation_id | UUID | FOREIGN KEY | 会话ID |
| user_id | UUID | FOREIGN KEY | 用户ID |
| content | TEXT | NOT NULL | 消息内容 |
| message_type | VARCHAR(20) | DEFAULT 'text' | 消息类型 |
| voice_data | BLOB | | 语音数据 |
| is_user | BOOLEAN | NOT NULL | 是否用户消息 |
| emotion | JSON | | 情感分析结果 |
| timestamp | DATETIME | NOT NULL | 发送时间 |

### 5.4 人设表（personas）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 主键 |
| user_id | UUID | NOT NULL | 用户ID |
| name | VARCHAR(50) | NOT NULL | AI名字 |
| age | INTEGER | | AI年龄 |
| identity | VARCHAR(100) | | AI身份 |
| backstory | VARCHAR(500) | | 背景故事 |
| personality | JSON | | 人格维度 |
| speaking_style | JSON | | 语言风格 |
| interests | JSON | | 兴趣爱好 |
| evolution_rate | FLOAT | DEFAULT 0.1 | 演化速率 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

### 5.5 记忆表（memories）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 主键 |
| user_id | UUID | NOT NULL | 用户ID |
| memory_type | VARCHAR(20) | NOT NULL | 记忆类型 |
| content | TEXT | NOT NULL | 记忆内容 |
| embedding | BLOB | | 向量嵌入 |
| metadata | JSON | | 元数据 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| accessed_at | DATETIME | NOT NULL | 访问时间 |

### 5.6 关怀事件表（care_events）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 主键 |
| user_id | UUID | NOT NULL | 用户ID |
| care_type | VARCHAR(20) | NOT NULL | 关怀类型 |
| title | VARCHAR(100) | | 标题 |
| content | TEXT | | 内容模板 |
| trigger_time | DATETIME | NOT NULL | 触发时间 |
| repeat_type | VARCHAR(20) | DEFAULT 'once' | 重复类型 |
| metadata | JSON | | 元数据 |
| status | VARCHAR(20) | DEFAULT 'pending' | 状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |

---

## 6. 技术选型

### 6.1 技术栈

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 后端框架 | FastAPI | ^0.104.1 | 异步支持、AI生态完善 |
| ASGI服务器 | Uvicorn | ^0.24.0 | 高性能异步服务器 |
| 数据验证 | Pydantic | ^2.5.2 | 数据模型验证 |
| ORM | SQLAlchemy | ^2.0.23 | 数据库操作 |
| 向量数据库 | Chroma | ^0.4.22 | 本地部署、易用 |
| LLM框架 | LangChain | ^0.1.0 | 链式调用、记忆管理 |
| 大模型 | 通义千问 | - | 国内可用、免费额度 |
| 语音识别 | Whisper | ^20231117 | 开源、准确率高 |
| 语音合成 | Edge-TTS | ^6.1.8 | 免费、效果好 |
| 缓存 | Redis | ^5.0.1 | 会话状态管理（可选） |
| 数据库 | SQLite/PostgreSQL | - | 轻量首选SQLite |

### 6.2 requirements.txt

```txt
fastapi>=0.104.1
uvicorn>=0.24.0
python-multipart>=0.0.6
pydantic>=2.5.2
pydantic-settings>=2.1.0
sqlalchemy>=2.0.23
chromadb>=0.4.22
langchain>=0.1.0
langchain-qianwen>=0.1.0
openai>=1.13.3
whisper>=20231117
edge-tts>=6.1.8
redis>=5.0.1
python-dotenv>=1.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

---

## 7. 部署与运行

### 7.1 环境变量配置（.env）

```env
# 应用配置
APP_NAME=校园情感陪伴助手
APP_VERSION=1.0.0
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///./data/sqlite/example_db.sqlite3

# 向量数据库配置
CHROMA_PATH=./data/chroma

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# LLM配置
LLM_API_KEY=your-qianwen-api-key
LLM_MODEL=qwen-plus

# 语音服务配置
VOICE_SERVICE=edge-tts
```

### 7.2 启动命令

```bash
# 开发模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 7.3 访问API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 8. 安全与性能

### 8.1 安全措施

| 措施 | 说明 |
|------|------|
| 用户认证 | 使用JWT Token进行用户身份验证 |
| 数据加密 | 敏感数据存储加密 |
| 输入验证 | 所有API输入进行严格验证，防止注入攻击 |
| 权限控制 | 基于角色的访问控制（RBAC） |
| 日志审计 | 记录关键操作日志，便于安全审计 |

### 8.2 性能优化

| 措施 | 说明 |
|------|------|
| 缓存策略 | 使用Redis缓存会话状态和频繁访问的数据 |
| 异步处理 | 使用FastAPI异步特性处理IO密集型操作 |
| 向量索引 | Chroma自动创建向量索引，优化检索性能 |
| 消息队列 | 对于非实时任务使用消息队列异步处理 |

---

## 附录

### A. 核心业务流程图

#### A.1 对话流程

```
用户发送消息
    │
    ▼
┌───────────────────────┐
│ 1. 消息接收与预处理     │
│    - 文字/语音识别      │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 2. 情感分析           │
│    - 识别用户情绪      │
│    - 更新AI情感状态    │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 3. 记忆检索           │
│    - 检索相关记忆      │
│    - 构建上下文       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 4. 技能匹配           │
│    - 意图识别         │
│    - 技能选择         │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 5. 响应生成           │
│    - 人设驱动         │
│    - LLM调用          │
│    - 情感化调整       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 6. 记忆存储           │
│    - 提取重要信息      │
│    - 存储到记忆系统    │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 7. 消息发送           │
│    - 文字/语音输出     │
└───────────────────────┘
```

#### A.2 主动关怀流程

```
定时任务触发
    │
    ▼
┌───────────────────────┐
│ 1. 检查关怀事件       │
│    - 时间触发         │
│    - 事件触发         │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 2. 获取用户画像       │
│    - 偏好信息         │
│    - 情感状态         │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 3. 生成关怀内容       │
│    - 个性化模板       │
│    - 情感适配         │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ 4. 发送关怀消息       │
│    - 推送通知         │
│    - 对话消息         │
└───────────────────────┘
```

---

**文档版本**: v1.0  
**创建日期**: 2024年  
**作者**: 校园情感陪伴助手开发团队
