# Chatbot 记忆模块设计草案

> 状态：待审核
> 范围：先做设计与边界确认，不包含业务代码改动
> 当前仓库观察时间：2026-07-07

## 1. 设计目标

我们的记忆系统核心：Make a ChatAgent more like a human。一切以该目标为主。

记忆模块要解决三个层次的问题：

1. **短期记忆**：让同一个会话线程里的多轮对话保持连续性，避免每轮都像新对话。
2. **长期记忆**：沉淀跨会话仍然有价值的信息，例如用户画像、用户当前状态、重要互动经历。
3. **可治理记忆**：每条长期记忆都能解释来源、更新时间、置信度、是否过期，并支持后续更新、删除、遗忘。

本阶段先实现：

- 短期记忆：基于 LangGraph checkpoint + 滑动窗口。
- 长期记忆：先落 semantic memory 和 episodic memory。
- Procedural memory：暂缓，只预留数据结构，因为它依赖 tool、skill、系统提示词治理能力。

本阶段同时明确一个边界：

- `love` 是好感度/关系状态，不属于记忆模块的真实数据源。
- 记忆模块可以在运行时接收 `love_snapshot`，用于还原当轮上下文或辅助 Prompt。
- `love` 的读取、计算、更新应由独立的好感度系统，或由用户画像系统中的关系模块负责。

## 2. 当前代码实现现状

### 2.1 已有主流程

当前核心 Agent 在 `app/agent/ChatAgent.py`：

- 使用 `StateGraph(EmotionState)` 构建 LangGraph 状态机。
- 节点包括：
  - `load_memory`：首次加载记忆，目前只初始化 `love=77`、空 `history`、空 `messages`。
  - `user_input`：把用户输入转换成 `HumanMessage`，并写入 `MemoryItem(type="Chat")`。
  - `emotion_analysis`：占位情感分析，当前固定写入“用户当前情感为：中性”。
  - `llm`：拼接系统提示词和当前 messages，调用绑定 tools 的 LLM。
  - `tools`：执行工具调用并写入 `ToolMessage` 和 `MemoryItem(type="ToolCall")`。
- `graph.compile(checkpointer=MemorySaver())` 已经接入 LangGraph checkpoint。
- 会话通过 `configurable.thread_id` 区分，例如 `{"configurable": {"thread_id": "czw197"}}`。

### 2.2 已有状态模型

当前 `app/memory/EmotionMemory.py` 定义：

- `messages: Annotated[list, add_messages]`
  - LangChain 消息列表，用于 LLM 上下文。
- `history: Annotated[List[MemoryItem], operator.add]`
  - 带元数据的对话/工具/情感记录。
- `love: Annotated[int, operator.add]`
  - 当前代码里把好感度作为 LangGraph state 累计值。
  - 目标设计中，`love` 不再由短期记忆模块持有真实状态，而是由好感度系统提供快照。
- `user_input: str`
  - 当前用户输入。

当前 `app/memory/MemoryItem.py` 定义：

- `type`
  - 当前注释中主要包括 `Chat`、`Think`、`ToolCall`，实际还有 `EmotionAnalysis`。
- `speaker`
  - `System`、`AI`、`User` 等。
- `message`
  - LangChain `BaseMessage`。
- `love`
  - 当前代码里记录当时好感度；目标设计中建议改名为 `love_snapshot`，表示外部好感度系统传入的快照。
- `ai_emo`、`user_emo`
  - 预留情绪信息。
- `speak_time`
  - 时间戳。
- `importance`
  - 重要性分数，默认 0.5。

### 2.3 已有服务接口

`app/services/external.py` 已经预留 `MemoryService` 抽象接口：

- `save_memory(user_id, memory_type, content, metadata)`
- `retrieve_memory(user_id, query, memory_type, top_k)`
- `update_memory(memory_id, content, metadata)`
- `delete_memory(memory_id)`
- `list_memories(user_id, memory_type)`

目前只有接口，没有具体实现，也没有和 `ChatAgent` 串起来。

### 2.4 Demo 中已有可借鉴逻辑

- `demos/simple_memory.py`
  - 演示 `create_react_agent(..., checkpointer=InMemorySaver())` 通过 `thread_id` 保留同一线程历史。
- `demos/hello.py`
  - 演示当 `messages` 超过阈值后，用 `RemoveMessage` 删除旧消息，只保留最近几条。
  - 这可以作为短期记忆滑动窗口的原型参考。
- `demos/love_chat.py`
  - 演示 `love` 状态用 `operator.add` 随对话累加。

### 2.5 当前缺口

当前代码还没有真正实现长期记忆：

- 没有 `user/` 或 `users/` 目录存储用户画像。
- 没有 semantic / episodic / procedural 的分类逻辑。
- 没有长期记忆写入、检索、召回、合并、遗忘机制。
- 没有向 LLM 注入长期记忆上下文。
- `MemorySaver` 目前只保存 LangGraph checkpoint，不等于长期记忆库。
- `self.memory_loaded` 是 `ChatAgent` 实例变量，不是按 `thread_id` 或 `user_id` 区分；多用户、多线程时可能产生串扰。
- 当前 `love` reducer 使用 `operator.add`，`_chat` 返回 `"love": 1`，所以含义是增量而不是绝对值；后续应迁移到独立好感度模块，短期 state 只保留只读快照或调试记录。

## 3. 记忆分层设计

### 3.1 总体分层

```text
用户输入
  ↓
运行时上下文装配：user_id + session_id
  ├─ 短期记忆层：LangGraph checkpoint + messages 滑动窗口
  ├─ 长期记忆检索层：semantic memory + episodic memory
  └─ 好感度/用户画像上下文：love_snapshot + profile summary
  ↓
Prompt 组装：系统提示词 + 好感度上下文 + 相关长期记忆 + 短期窗口
  ↓
LLM 回复 / 工具调用
  ↓
后处理
  ├─ 记忆写入层：分类、抽取、去重、合并、落盘、索引
  └─ 好感度系统：根据交互事件更新 love
```

### 3.2 短期记忆

短期记忆用于当前 session/thread 内的即时上下文。

建议职责：

- 保存最近 N 轮对话消息。
- 保存当前会话内的临时状态，例如临时情绪分析、最近工具调用结果、session summary。
- 可以保存 `love_snapshot` 作为当轮上下文快照，但不负责计算、累加或持久化 `love`。
- 在 messages 超过阈值时裁剪旧消息，保留最近窗口。
- 被裁剪的旧内容如有价值，应先进入长期记忆候选；裁剪前触发一次长期记忆筛选和写入流程。

重要澄清：

- `MemorySaver` / `InMemorySaver` 负责把 LangGraph state checkpoint 保存起来。
- “滑动窗口”不是 `MemorySaver` 自动完成的，而是需要我们在图中增加 `trim_messages` / `compress_messages` 节点或在 LLM 调用前统一裁剪。
- 短期记忆里的 `love_snapshot` 只是快照，不是权威状态；恢复 checkpoint 时也需要重新从好感度系统读取最新值。

建议参数：

| 参数 | 建议值 | 说明 |
| --- | --- | --- |
| `recent_turns` | 8-12 | 保留最近 8-12 轮用户/AI对话 |
| `max_messages` | 20-30 | 包含工具消息、情感分析消息后的上限 |
| `summary_threshold` | 30 messages | 超过阈值后生成会话摘要 |
| `thread_id` | `session_id` | 用于 LangGraph checkpoint |
| `user_id` | 业务用户 ID | 用于长期记忆归属 |
| `love_snapshot` | 外部传入 | 来源是好感度系统或用户画像关系模块 |

### 3.3 长期记忆

长期记忆跨 session 保存，按用户归属管理。

本阶段分两类：

1. **Semantic memory**
   - 存“事实”和“稳定画像”。
   - 例：用户专业、年级、偏好、长期目标、常提到的压力来源。
2. **Episodic memory**
   - 存“发生过的互动经历”。
   - 例：某次对话里用户因为考试焦虑，Agent 做了安慰和学习计划，用户反馈有效。

暂缓：

3. **Procedural memory**
   - 存“用户教会 Agent 的规则、偏好工作流、工具使用方式”。
   - 例：用户说“以后帮我写日报都按这个格式来”。
   - 当前先不实现，因为它需要和 tool、skill、系统提示词版本管理打通。

### 3.4 好感度系统与记忆模块边界

`love` 建议作为独立的好感度系统来设计，而不是短期记忆或长期记忆的一个字段。

好感度系统的职责：

- 以 `user_id` 为 key 维护全局关系状态，一个用户一个主要 `love` 值。
- 根据用户行为、互动频率、反馈、情绪变化、Agent 行动结果计算增减。
- 输出当前 `love_snapshot` 给 ChatAgent，用于 Prompt 组装和回复风格控制。
- 保存好感度变化原因，方便调试和后续解释。

记忆模块的职责：

- 可以记录“当时的 `love_snapshot`”，用于还原一段 episodic memory 的上下文。
- 可以向好感度系统提供事件信号，例如“用户明确感谢”“用户表达不满”“用户纠正偏好”。
- 不直接累加、覆盖或持久化权威 `love` 值。

建议的好感度数据结构先由独立模块维护：

```json
{
  "user_id": "u_001",
  "love": 77,
  "baseline": 70,
  "volatility": 0.2,
  "last_delta": 1,
  "last_reason": "用户对回复表达感谢",
  "updated_at": "2026-07-07T12:00:00+08:00"
}
```

其中：

- `love` 是当前全局好感度。
- `baseline` 表示长期稳定关系水平。
- `volatility` 表示短期情绪波动幅度。
- `last_delta` 和 `last_reason` 用于记录最近一次变化。

这样 ChatAgent 会更像一个具体的人：长期关系相对稳定，但会因近期互动产生短期波动。

## 4. 记忆分类场景细化

### 4.1 Semantic memory 场景

本阶段不强行敲定完整用户画像 schema。记忆模块先负责保存可检索、可更新的长期事实；用户画像和好感度系统可以从这些事实中读取或同步，但它们不必和记忆模块共用同一个文件结构。

| 场景 | 示例 | 建议存储位置 | 说明 |
| --- | --- | --- | --- |
| 用户基础画像 | “我叫小王，是大二学生” | semantic / profile 候选 | 稳定、可更新 |
| 用户偏好 | “我喜欢你回答短一点” | semantic | 影响回复风格 |
| 用户长期目标 | “我想考研” | semantic | 后续可长期召回 |
| 用户当前状态 | “最近我压力很大” | semantic state | 需要过期时间 |
| 关系状态 | 好感度、信任度、互动频率 | 好感度系统 | 记忆模块只引用快照和事件证据 |
| 敏感事实 | 健康、家庭、财务等 | semantic with sensitivity | 需要更严格的写入策略 |

### 4.2 Episodic memory 场景

| 场景 | 示例 | 建议存储位置 | 说明 |
| --- | --- | --- | --- |
| 重要对话事件 | “用户昨晚失眠，Agent 做了陪伴” | episodic | 存摘要，不存全量聊天 |
| Agent 行动结果 | “Agent 制定了复习计划，用户接受” | episodic | 可复用经验 |
| 工具调用经历 | “查了某课程资料并给出结论” | episodic | 保存工具、输入、结果摘要 |
| 情绪变化 | “用户从焦虑变为平静” | episodic | 情感陪伴场景重要 |
| 用户反馈 | “这个建议对我有用” | episodic | 提升后续策略 |
| 冲突/纠正 | “用户指出不喜欢被叫昵称” | episodic + semantic | episodic 记录发生过程，semantic 更新偏好 |

### 4.3 Procedural memory 场景

| 场景 | 示例 | 当前处理 |
| --- | --- | --- |
| 固定输出格式 | “以后周报按三段式输出” | 暂缓，先标记为候选 |
| 工具使用规则 | “查资料优先用学校官网” | 暂缓，未来进入 skill/tool policy |
| 个性化对话原则 | “我难过时不要讲大道理” | 可先存 semantic preference |
| 长期任务流程 | “每天晚上提醒我复盘” | 暂缓，未来需要任务/自动化系统 |

## 5. 文件结构设计

建议先采用 file-first 的 MVP。初版按“一个用户一个 JSON”跑通记忆模块逻辑，后续再扩展为目录、JSONL 或数据库。

MVP 结构：

```text
data/
  memory/
    users/
      {user_id}.json
```

单个用户文件中保存：

- semantic memories
- episodic memories
- procedural candidates
- schema version
- 简单索引元数据

不在该文件中保存权威 `love` 值。`love` 属于好感度系统，记忆文件最多保存某条 episodic memory 发生时的 `love_snapshot`。

未来扩展结构：

```text
data/
  memory/
    users/
      {user_id}/
        semantic.jsonl
        episodic.jsonl
        procedural.md        # 预留，暂不启用
        sessions/
          {session_id}.jsonl # 可选：归档原始或压缩后的会话事件
        indexes/
          manifest.json      # 可选：记录向量索引、schema 版本等
```

### 5.1 为什么建议 JSON/JSONL 而不是只用 Markdown

JSON/JSONL 优点：

- 适合程序读写、更新、去重和检索。
- 每条记忆可以独立追加，便于审计和回滚。
- 可以稳定保存 `id`、`confidence`、`source_message_ids` 等字段。

Markdown 优点：

- 人类可读，适合审核用户画像或 procedural rules。

建议：

- 初版 `{user_id}.json`：机器可读，方便直接实现增删改查。
- 后续 `semantic.jsonl` / `episodic.jsonl`：长期记忆事件流，便于追加、审计和迁移。
- 后续 `procedural.md`：未来保存可读规则，但当前不进入执行链路。

## 6. 数据结构设计

### 6.1 用户记忆文件 `{user_id}.json`

```json
{
  "schema_version": "0.1",
  "user_id": "u_001",
  "semantic_memories": [],
  "episodic_memories": [],
  "procedural_candidates": [],
  "index": {
    "semantic_count": 0,
    "episodic_count": 0,
    "last_compacted_at": null
  },
  "created_at": null,
  "updated_at": null
}
```

说明：

- 这个文件只服务记忆模块，不强行承载完整用户画像。
- 如果后续有独立用户画像系统，它可以从 semantic memories 中同步姓名、年级、偏好等字段。
- 如果后续有独立好感度系统，它可以读取 episodic memories 里的互动事件，但权威 `love` 值不写在这里。

### 6.2 Semantic memory item

```json
{
  "id": "sem_20260705_000001",
  "user_id": "u_001",
  "type": "semantic",
  "scope": "profile_candidate|preference|state|fact",
  "content": "用户最近因为期末考试感到压力大。",
  "subject": "user",
  "predicate": "current_state",
  "object": "期末考试压力大",
  "confidence": 0.82,
  "importance": 0.7,
  "sensitivity": "normal|sensitive",
  "status": "active|superseded|deleted",
  "evidence": {
    "session_id": "s_001",
    "message_ids": ["msg_001"],
    "excerpt": "最近期末压力很大"
  },
  "created_at": "2026-07-05T12:00:00+08:00",
  "updated_at": "2026-07-05T12:00:00+08:00",
  "last_used_at": null,
  "expires_at": "2026-08-05T12:00:00+08:00",
  "tags": ["exam", "stress"],
  "embedding_text": "用户最近因为期末考试感到压力大。"
}
```

### 6.3 Episodic memory item

```json
{
  "id": "epi_20260705_000001",
  "user_id": "u_001",
  "type": "episodic",
  "session_id": "s_001",
  "title": "期末压力陪伴对话",
  "summary": "用户表达期末考试压力，Agent 先共情，再帮助拆分复习计划，用户反馈心情好一些。",
  "turn_range": [3, 8],
  "user_goal": "缓解考试焦虑并获得复习建议",
  "agent_actions": ["情绪安抚", "制定复习拆分计划"],
  "outcome": "用户反馈有帮助",
  "emotion_before": {"anxiety": 0.8},
  "emotion_after": {"calm": 0.6},
  "love_snapshot": 77,
  "tools_called": [],
  "importance": 0.8,
  "confidence": 0.9,
  "status": "active|deleted",
  "evidence": {
    "message_ids": ["msg_003", "msg_008"],
    "excerpt": "谢谢你，我感觉好多了"
  },
  "created_at": "2026-07-05T12:20:00+08:00",
  "last_used_at": null,
  "recall_triggers": ["期末", "考试压力", "焦虑", "复习计划"]
}
```

### 6.4 当前 `MemoryItem` 与长期记忆 item 的关系

`MemoryItem` 更适合表示一次 LangGraph 会话内的原始事件：

- 用户说了什么。
- AI 回了什么。
- 工具调用返回什么。
- 当时 emotion 是什么，以及外部好感度系统传入的 `love_snapshot` 是多少。

长期记忆 item 更适合表示经过筛选后的“可复用知识”：

- 从多条 `MemoryItem` 中抽取事实，形成 semantic memory。
- 从一段对话 `MemoryItem` 中总结经历，形成 episodic memory。

因此建议不要直接把所有 `MemoryItem` 原样塞进长期记忆库，而是经过分类、摘要、去重、合并后再写入。

## 7. 运行机制设计

### 7.1 单轮对话流程

```text
1. 接收 user_id、session_id、user_input
2. 用 session_id 作为 LangGraph thread_id 读取短期 checkpoint
3. 从好感度系统或用户画像系统读取 love_snapshot / profile summary
4. 基于 user_input 检索 semantic / episodic memory
5. 组装 Prompt：
   - system prompt
   - love_snapshot / profile summary
   - 相关 semantic facts
   - 相关 episodic summaries
   - 当前短期 messages window
6. 调用 LLM / tools
7. 写入短期 checkpoint
8. 运行 memory writer：
   - 分类是否值得长期保存
   - 抽取 semantic facts
   - 生成 episodic summary
   - 更新用户记忆 JSON / index
9. 运行好感度系统：
   - 接收本轮互动事件
   - 计算 love delta
   - 更新全局 love
```

### 7.2 长期记忆写入策略

长期记忆写入主要由短期窗口裁剪触发：

- 当 `messages` 超过窗口阈值时，裁剪前先对即将移出窗口的内容做筛选。
- 有价值的内容写入 semantic / episodic memory。
- 低价值内容只丢弃或进入 session summary，不写长期记忆。

也可以有强触发条件：

- 用户明确说“记住……”。
- 用户明确纠正已有记忆。
- 用户对 Agent 的互动方式给出强反馈。
- 本轮产生了明确计划、承诺、工具结果或情绪转折。

建议不是每一句都写长期记忆，而是满足条件才写，即有一个筛选条件。

应该写入：

- 用户明确说“记住……”。
- 用户提供稳定身份、偏好、长期目标。
- 用户表达较强或反复出现的情绪状态。
- 用户对 Agent 的回复策略给出正/负反馈。
- 一段对话产生明确结果，例如计划、承诺、解决方案。

谨慎写入：

- 一次性闲聊。
- 模糊、不确定、玩笑式表达。
- 敏感信息，除非用户明确要求保存，或产品策略允许并有保护。

不建议写入：

- 工具中间噪声。
- LLM 自己猜测出的用户事实。
- 没有用户证据支持的推断。
- 已过期的临时状态，除非作为 episodic 事件摘要。

特殊：

- LLM 涌现出来的内容不能直接入库。
- 如果模型推断出可能有价值但缺少用户证据的信息，可以向用户确认，例如：“那我以后记住你更喜欢先听安慰、再听建议，好不好？”
- 用户确认后再写入 semantic memory；用户未确认则只保留在短期上下文或丢弃。

### 7.3 长期记忆分类器

可以先用规则 + LLM 分类混合方案：

```json
{
  "should_store": true,
  "memory_types": ["semantic", "episodic"],
  "reason": "用户表达了近期稳定压力源，并且本轮对话形成了安抚结果",
  "confidence": 0.86
}
```

分类维度：

- 是否值得长期保存。
- 属于 semantic、episodic、procedural candidate 中哪一类。
- 是否生成 profile candidate，供未来用户画像系统消费。
- 是否需要过期时间。
- 是否涉及敏感信息。

### 7.4 长期记忆检索策略

建议分三路召回：

1. **好感度/画像上下文加载**
   - 每轮从好感度系统读取 `love_snapshot`。
   - 如果已有用户画像系统，则加载简短 profile summary。
   - 不把完整用户画像全量塞进 prompt。
2. **Semantic 检索**
   - query = 当前用户输入 + 当前 session 摘要。
   - 优先召回偏好、当前状态、长期目标、相关事实。
3. **Episodic 检索**
   - query = 当前用户输入 + 情绪标签 + 主题标签。
   - 召回过去类似情境和有效互动方式。

MVP 可以先做关键词过滤 + importance 排序；后续接 `CHROMA_PATH` 做向量检索。

### 7.5 Prompt 注入格式

建议将长期记忆作为系统上下文的一部分，格式保持短而可控：

```text
[好感度/关系状态]
- 当前好感度：77/100。
- 长期关系稳定，近期互动略有正向提升。

[用户画像摘要]
- 用户偏好：回答简洁、语气温和。
- 当前状态：最近因期末考试压力较大，信息更新时间 2026-07-05。

[相关长期记忆]
- semantic: 用户正在准备期末考试，压力源主要是复习进度。
- episodic: 上次用户焦虑时，先共情再拆分计划的回复方式有效。
```

注意：

- 不要把内部字段如 `confidence`、`evidence` 直接暴露给模型，除非用于调试。
- 不要注入过多旧记忆，避免模型被无关信息带偏。
- 对过期状态要降权或不注入。
- `love_snapshot` 来自好感度系统，不从长期记忆反推。

### 7.6 记忆更新与冲突处理

长期记忆不是只追加，还要能更新。

建议规则：

- 同一 subject + predicate 出现新事实时，旧记录标记为 `superseded`。
- 用户明确纠正时，新记录置信度更高。
- 当前状态类记忆必须有 `expires_at`。
- 偏好类记忆如果多次被强化，提高 `confidence` 和 `importance`。
- 长时间未使用且低重要性的记忆可进入归档。

例：

```text
旧：用户喜欢被叫“小王”
新：用户说“别叫我小王，叫我阿辰”

处理：
- 旧 semantic.status = superseded
- 新 semantic.scope = preference
- 写入一条 profile candidate，供用户画像系统后续同步为 nicknames = ["阿辰"]
```

## 8. 与当前代码的改造映射

| 当前位置 | 当前职责 | 后续建议 |
| --- | --- | --- |
| `app/agent/ChatAgent.py` | LangGraph 主流程 | 增加长期记忆加载、检索、写入节点 |
| `app/memory/EmotionMemory.py` | 短期 state 定义 | 增加 `user_id`、`session_id`、`memory_context`、`session_summary`；将 `love` 从可累加 state 迁移为只读 `love_snapshot` |
| `app/memory/MemoryItem.py` | 原始事件记录 | 保留为 session event，不直接等同长期记忆 |
| `app/services/external.py::MemoryService` | 抽象接口 | 实现 FileMemoryService / ChromaMemoryService |
| `app/config.py` | 预留 DB、Chroma、Redis 配置 | 增加 `MEMORY_ROOT`、窗口大小、召回数量 |
| `demos/hello.py` | 消息压缩 demo | 抽成正式 `trim_messages` 节点 |
| 新增好感度模块 | 当前未实现 | 提供 `get_love(user_id)`、`update_love(user_id, event)`，记忆模块只消费快照和发送事件 |

建议新增模块：

```text
app/
  memory/
    schema.py              # 长期记忆数据结构
    store.py               # 文件存储实现
    classifier.py          # 记忆分类与抽取
    retriever.py           # 长期记忆检索
    profile_candidate.py   # 输出用户画像候选，不直接绑定画像系统
    window.py              # 短期消息窗口裁剪
  affinity/
    service.py             # 好感度读取和更新
    schema.py              # 好感度状态和事件结构
```

## 9. LangGraph 节点建议

未来 ChatAgent 可演进为：

```text
START
  ↓
load_short_term_state
  ↓
load_affinity_context
  ↓
retrieve_long_term_memory
  ↓
user_input
  ↓
emotion_analysis
  ↓
llm
  ↓
tools? ── yes ──> tools ──> llm
  ↓ no
memory_write_decision
  ↓
write_long_term_memory
  ↓
update_affinity
  ↓
trim_short_term_window
  ↓
END
```

MVP 可以简化为：

```text
START
  ↓
load_runtime_context
  ↓
user_input
  ↓
llm
  ↓
write_memory_candidates
  ↓
emit_affinity_event
  ↓
trim_messages
  ↓
END
```

## 10. 用户记忆文件设计取舍

用户提出“新建 user 文件夹，一个用户存一个 json 或 md”。结合当前阶段，建议初版采用：

```text
data/memory/users/{user_id}.json
```

原因：

- 当前目标是先跑通记忆模块，不急着敲定完整用户画像 schema。
- 单文件便于调试、备份和人工查看。
- 文件内部保留 `schema_version` 和分区字段，后续可以平滑拆成目录或迁移数据库。
- 权威 `love` 不写入该文件，避免记忆模块和好感度系统互相污染。

未来当单文件变大时，再迁移为：

```text
data/memory/users/{user_id}/
  semantic.jsonl
  episodic.jsonl
  procedural.md
  indexes/manifest.json
```

迁移标准：

- 单个用户记忆文件增长到不方便人工查看。
- 需要按类型增量追加、审计或回滚。
- 需要接入向量库、数据库或后台管理页面。

## 11. 风险与注意事项

### 11.1 隐私与安全

- 用户画像和长期记忆属于敏感数据。
- 至少需要支持“查看我的记忆”“删除某条记忆”“忘记我”。
- 敏感字段要标记 `sensitivity`。
- 不应保存无来源的模型推断。
- 对模型推断出的个人偏好或状态，应优先询问用户是否记住。

### 11.2 多用户隔离

- 短期记忆用 `session_id/thread_id` 隔离。
- 长期记忆必须用 `user_id` 隔离。
- 好感度系统也必须用 `user_id` 隔离。
- 当前 `self.memory_loaded` 是实例级状态，不适合多用户。

### 11.3 记忆污染

- LLM 可能把玩笑、角色扮演、临时情绪误写成长期事实。
- 需要 `confidence`、`expires_at`、`evidence`、`status`。
- 对用户纠正要优先级最高。

### 11.4 上下文膨胀

- 长期记忆不能全量注入。
- 每轮只注入 profile 摘要 + top K 相关记忆。
- episodic memory 应注入摘要，不注入原始长对话。

## 12. 建议实施阶段

### Phase 1：文档和 schema 固化

- 审核本文档。
- 确认初版一用户一个记忆 JSON。
- 确认 semantic / episodic 字段。
- 确认短期窗口大小和长期召回 top_k。
- 确认好感度系统和记忆模块的边界：记忆模块只接收 `love_snapshot`，不维护权威 `love`。

### Phase 2：短期记忆整理

- 将滑动窗口从 demo 抽成正式模块。
- 修正 `memory_loaded` 的多 session 问题。
- 将 `love` 从 `operator.add` 的短期 state 中迁出，改为外部传入的只读 `love_snapshot`。
- 保证 checkpoint 只负责短期会话状态。
- 裁剪窗口前触发长期记忆候选筛选。

### Phase 3：文件版长期记忆

- 实现 `FileMemoryService`。
- 创建 `data/memory/users/{user_id}.json`。
- 支持 semantic / episodic 写入、读取、更新和删除。
- 实现基础关键词召回。
- 预留后续迁移 JSONL / 数据库的接口。

### Phase 4：记忆抽取与合并

- 增加 memory classifier。
- 增加 semantic 抽取和 profile candidate 输出。
- 增加 episodic 摘要。
- 增加冲突、过期、删除逻辑。
- 对 LLM 涌现内容增加用户确认流程。

### Phase 5：好感度系统接入

- 定义 `AffinityService` 接口。
- 从好感度系统读取 `love_snapshot` 注入 Prompt。
- 将用户反馈、情绪转折、互动结果作为事件发送给好感度系统。
- 保证记忆模块和好感度模块可以独立测试。

### Phase 6：向量检索与可视化审核

- 接入 Chroma 或其他向量库。
- 为每条记忆生成 embedding。
- 增加记忆查看、编辑、删除接口。

## 13. 已确认决策与待确认问题

| 问题 | 当前决策 |
| --- | --- |
| 用户记忆文件结构 | 初版一用户一个 JSON，后续可扩展为目录或数据库。 |
| 初版是否接数据库 | 初版允许只用 JSON 文件跑通逻辑，但接口要方便后续接数据库。 |
| `love` 属于全局还是 session | `love` 是全局用户关系值，一个用户一个主要好感度。 |
| `love` 属于记忆模块吗 | 不属于。记忆模块只接收 `love_snapshot`，权威值由好感度系统或用户画像关系模块维护。 |
| 情感状态如何处理 | 可以有短期情绪波动，也可以由好感度系统维护长期稳定关系。 |
| sensitive semantic memory | 暂不做复杂授权，但需要预留后台增删改查；模型推断内容可以先询问用户是否记住。 |
| procedural memory | 本阶段只实现框架和候选标记，不参与 Prompt 注入。 |

仍待后续确认：

- 好感度系统的具体打分规则。
- 后台记忆管理接口的粒度。
- semantic memory 和用户画像系统之间的同步方式。
