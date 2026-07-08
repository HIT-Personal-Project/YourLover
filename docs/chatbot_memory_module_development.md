# Chatbot 记忆模块开发文档

> 状态：开发任务草案
> 来源设计文档：`docs/chatbot_memory_module_design.md`
> 当前日期：2026-07-08
> 核心目标：Make a ChatAgent more like a human

## 1. 开发目标

本开发文档把记忆模块拆成可独立实现、测试和替换的任务包。MVP 目标不是一次性做完整智能记忆系统，而是先跑通：

1. 短期记忆窗口：同一 session 内保持连续对话，并能裁剪旧消息。
2. 长期记忆文件存储：一用户一个 JSON 文件，保存 semantic / episodic / procedural candidate。
3. 长期记忆检索：能按当前输入召回相关事实和经历。
4. 长期记忆写入：能从被裁剪消息或强触发消息中生成候选记忆。
5. ChatAgent 集成：对话前注入记忆，对话后写入候选记忆。
6. 好感度边界：`love` 不属于记忆模块，记忆模块只接收 `love_snapshot`。

## 2. 本期范围

本期实现：

- `app/memory/schema.py`
- `app/memory/store.py`
- `app/memory/window.py`
- `app/memory/retriever.py`
- `app/memory/classifier.py`
- `app/memory/profile_candidate.py`
- `app/affinity/schema.py`
- `app/affinity/service.py`
- ChatAgent 的最小集成
- 单元测试和 MVP demo

本期不实现：

- 真实好感度算法。
- 向量库检索。
- 后台管理页面。
- 数据库版存储。
- 完整用户画像系统。
- procedural memory 的 Prompt 注入。

## 3. 架构边界

### 3.1 Memory 模块负责

- 管理用户长期记忆文件。
- 定义 semantic / episodic / procedural candidate 数据结构。
- 按 `user_id` 读写、检索、更新、删除记忆。
- 从短期消息中生成长期记忆候选。
- 把相关长期记忆格式化为 Prompt 上下文。

### 3.2 Memory 模块不负责

- 不维护权威 `love`。
- 不计算好感度变化。
- 不直接决定用户画像最终字段。
- 不保存所有原始聊天记录作为长期记忆。
- 不把 LLM 推断内容直接入库。

### 3.3 Affinity 模块负责

- 提供 `love_snapshot`。
- 接收记忆模块或 ChatAgent 发送的互动事件。
- 后续替换为真实好感度系统。

MVP 阶段 Affinity 可以是桩实现，默认返回 `love=77`。

## 4. 数据文件约定

初版文件结构：

```text
data/
  memory/
    users/
      {user_id}.json
```

用户记忆文件结构：

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

注意：

- 真实用户记忆数据不应提交到 Git。
- 如果项目后续增加 `.gitignore`，建议忽略 `data/memory/users/*.json`。
- 测试数据应写入临时目录或 fixtures。

## 5. 开发任务拆分

## Task M1：记忆数据契约

**目标**
固定记忆模块内部 schema，后续模块都依赖它。

**建议文件**

- `app/memory/schema.py`

**主要对象**

- `MemoryType`
- `MemoryStatus`
- `MemoryEvidence`
- `SemanticMemory`
- `EpisodicMemory`
- `ProceduralCandidate`
- `UserMemoryIndex`
- `UserMemoryFile`

**输入**

- `user_id`
- 原始文本或摘要
- evidence 元数据

**输出**

- 可序列化为 JSON 的 memory object。

**边界**

- 不读写文件。
- 不调用 LLM。
- 不依赖 LangGraph。
- 不处理好感度计算。

**交付物**

- 类型定义。
- `to_dict` / `from_dict` 或等价序列化方法。
- 基础字段默认值，例如 `created_at`、`updated_at`、`status`。

**验收标准**

- 能构造 semantic memory。
- 能构造 episodic memory，并包含 `love_snapshot`。
- 能构造完整 `UserMemoryFile`。
- JSON 序列化后结构和设计文档一致。

## Task M2：文件版 MemoryStore

**目标**
实现一用户一个 JSON 的长期记忆存储。

**建议文件**

- `app/memory/store.py`

**主要接口**

```python
class FileMemoryStore:
    def load_user_memory(self, user_id: str) -> UserMemoryFile: ...
    def save_user_memory(self, memory_file: UserMemoryFile) -> None: ...
    def add_memory(self, user_id: str, memory) -> str: ...
    def update_memory(self, user_id: str, memory_id: str, updates: dict) -> bool: ...
    def delete_memory(self, user_id: str, memory_id: str) -> bool: ...
    def list_memories(self, user_id: str, memory_type: str | None = None) -> list: ...
```

**输入**

- `user_id`
- memory object
- updates

**输出**

- memory id
- memory list
- operation status

**边界**

- 不判断内容是否值得保存。
- 不做检索排序。
- 不做向量索引。
- 不写好感度文件。

**交付物**

- 自动创建 `data/memory/users/{user_id}.json`。
- 支持 add / update / delete / list。
- 保存时更新 `updated_at` 和 `index` 计数。
- 文件损坏时给出明确错误。

**验收标准**

- 新用户首次访问会创建空记忆文件。
- 添加 semantic 后可从文件读回。
- 添加 episodic 后可从文件读回。
- 删除采用软删除：`status = "deleted"`。
- 不同 `user_id` 文件相互隔离。

## Task M3：短期记忆窗口模块

**目标**
从 demo 中抽出正式的短期消息裁剪逻辑。

**建议文件**

- `app/memory/window.py`

**主要接口**

```python
def trim_messages(messages: list, max_messages: int, keep_recent_turns: int) -> tuple[list, list]: ...
def should_trim(messages: list, max_messages: int) -> bool: ...
def select_messages_for_memory_write(removed_messages: list) -> list: ...
```

**输入**

- LangChain messages
- 窗口参数

**输出**

- retained messages
- removed messages

**边界**

- 不写长期记忆。
- 不调用 MemoryStore。
- 不调用 LLM。

**交付物**

- 可复用的 window 工具函数。
- 保留最近 N 轮消息。
- 返回被裁剪消息，交给 classifier。

**验收标准**

- 消息未超过阈值时不裁剪。
- 超过阈值时保留最近窗口。
- 被裁剪消息顺序稳定。
- 工具消息和 AI 消息不被错误拆散到无法理解。

## Task M4：长期记忆检索模块

**目标**
MVP 用关键词和 importance 排序召回相关长期记忆。

**建议文件**

- `app/memory/retriever.py`

**主要接口**

```python
class MemoryRetriever:
    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        memory_type: str | None = None,
        top_k: int = 5,
    ) -> list: ...

    def format_memory_context(self, memories: list) -> str: ...
```

**输入**

- `user_id`
- 当前用户输入
- 可选 memory type
- top_k

**输出**

- 相关 memory list
- Prompt 可用的 memory context 字符串

**边界**

- 不做写入。
- 不做向量检索。
- 不读取好感度。
- 不暴露内部 evidence 给模型，除非调试模式。

**交付物**

- semantic / episodic 分类型召回。
- 关键词命中 + importance + recency 的简单排序。
- Prompt context formatter。

**验收标准**

- 查询“考试压力”能召回相关 state / episodic。
- top_k 生效。
- 已 deleted 的记忆不召回。
- 过期记忆默认不召回，或显著降权。

## Task M5：记忆写入决策与抽取

**目标**
判断哪些短期消息值得进入长期记忆，并生成候选对象。

**建议文件**

- `app/memory/classifier.py`
- `app/memory/profile_candidate.py`

**主要接口**

```python
class MemoryClassifier:
    def classify_memory_candidate(self, messages: list) -> list: ...
    def extract_semantic_memories(self, messages: list, user_id: str) -> list[SemanticMemory]: ...
    def summarize_episodic_memory(self, messages: list, user_id: str, love_snapshot: int | None = None) -> EpisodicMemory | None: ...
```

**输入**

- 被裁剪消息
- 强触发消息
- `user_id`
- `love_snapshot`

**输出**

- semantic memory candidates
- episodic memory candidate
- procedural candidates
- needs_user_confirmation 标记

**边界**

- 不直接保存到文件。
- 不更新用户画像。
- 不更新好感度。

**MVP 策略**

先用规则实现：

- 出现“记住”“以后你要记得”等，生成 semantic。
- 出现“我叫”“我是”“我喜欢”“我不喜欢”“我最近”“我想”等，生成 semantic。
- 一段被裁剪消息中有明显问题、建议、结果，生成 episodic summary。
- 模型推断内容标记为 `needs_user_confirmation`，不直接入库。

后续可以替换为 LLM classifier。

**交付物**

- 规则版分类器。
- semantic 抽取。
- episodic 摘要生成。
- profile candidate 输出。

**验收标准**

- “记住我喜欢简短回答”生成 preference semantic。
- “我最近因为期末很焦虑”生成 state semantic，带 `expires_at`。
- 一段焦虑到缓解的对话生成 episodic。
- “模型猜测用户喜欢 X”不直接入库。

## Task M6：Affinity 接口桩

**目标**
明确好感度系统边界，让 ChatAgent 能读取 `love_snapshot`，但不把好感度实现混进 memory 模块。

**建议文件**

- `app/affinity/schema.py`
- `app/affinity/service.py`

**主要接口**

```python
class AffinityService:
    def get_love_snapshot(self, user_id: str) -> int: ...
    def emit_affinity_event(self, user_id: str, event: dict) -> None: ...
```

**输入**

- `user_id`
- interaction event

**输出**

- `love_snapshot`

**边界**

- 不写 memory JSON。
- 不读取 semantic / episodic 作为权威状态。
- 不实现复杂打分。

**交付物**

- 默认返回 `77` 的 MVP 实现。
- 接收事件但可以只记录日志或内存列表。
- 后续可替换为真实好感度算法。

**验收标准**

- ChatAgent 可以拿到 `love_snapshot`。
- 记忆写入完成后可以发送 affinity event。
- 替换 AffinityService 不影响 MemoryStore。

## Task M7：ChatAgent 集成

**目标**
把记忆读取、Prompt 注入、短期裁剪、长期写入接入当前 LangGraph 工作流。

**建议修改**

- `app/agent/ChatAgent.py`
- `app/memory/EmotionMemory.py`
- 必要时更新 `app/main.py` demo

**新增 state 字段**

- `user_id`
- `session_id`
- `memory_context`
- `session_summary`
- `love_snapshot`

**建议节点**

```text
START
  ↓
load_runtime_context
  ↓
retrieve_long_term_memory
  ↓
user_input
  ↓
emotion_analysis
  ↓
llm
  ↓
tools?
  ↓
write_memory_candidates
  ↓
emit_affinity_event
  ↓
trim_short_term_window
  ↓
END
```

**边界**

- 不在 ChatAgent 里实现文件细节。
- 不在 ChatAgent 里实现好感度算法。
- 不把所有 `history` 直接当长期记忆写入。

**交付物**

- ChatAgent 初始化时可注入 MemoryStore / Retriever / Classifier / AffinityService。
- LLM 调用前注入 memory context 和 love snapshot。
- LLM 调用后执行裁剪和候选写入。
- 移除或废弃 `love` 的 `operator.add` 语义。

**验收标准**

- 第一轮用户说“记住我喜欢回答短一点”后，长期记忆文件出现 semantic。
- 后续新 session 中问普通问题，Prompt 能注入“用户喜欢回答短一点”。
- `love_snapshot` 出现在 Prompt 组装中，但不写为权威长期记忆。
- 多个 `user_id` 的长期记忆互不污染。

## Task M8：测试与 MVP Demo

**目标**
保证每个模块都能独立验证，并提供一个端到端 demo。

**建议文件**

- `tests/test_memory_schema.py`
- `tests/test_memory_store.py`
- `tests/test_memory_window.py`
- `tests/test_memory_retriever.py`
- `tests/test_memory_classifier.py`
- `tests/test_affinity_service.py`
- `demos/memory_mvp_demo.py`

**测试边界**

- Store / Window / Retriever / Classifier 应尽量不依赖真实 LLM。
- 测试记忆文件写入临时目录。
- ChatAgent 集成测试可以使用 fake LLM 或最小 stub。

**验收标准**

- 能创建用户记忆文件。
- 能写入、读取、更新、删除 semantic / episodic。
- 能裁剪短期窗口并返回 removed messages。
- 能从 removed messages 生成候选记忆。
- 能检索相关记忆并格式化为 Prompt context。
- demo 能展示跨 session 召回。

## 6. 建议开发顺序

| 顺序 | 任务 | 原因 |
| --- | --- | --- |
| 1 | M1 schema | 所有模块依赖数据契约 |
| 2 | M2 store | 先让长期记忆能落盘 |
| 3 | M3 window | 先解决短期裁剪边界 |
| 4 | M4 retriever | 先能从长期记忆读出上下文 |
| 5 | M5 classifier | 再做写入决策和候选生成 |
| 6 | M6 affinity stub | 给 ChatAgent 集成提供 love_snapshot |
| 7 | M7 ChatAgent 集成 | 组合前面模块 |
| 8 | M8 tests/demo | 补齐模块测试和端到端验收 |

## 7. 里程碑

### Milestone A：记忆核心可独立运行

包含：

- M1 schema
- M2 store
- M3 window
- M4 retriever

验收：

- 不启动 ChatAgent，也能完整完成记忆文件 CRUD 和检索。

### Milestone B：长期记忆能自动产生

包含：

- M5 classifier

验收：

- 被裁剪的消息能生成 semantic / episodic 候选。
- 明确“记住”类输入能生成 semantic。

### Milestone C：ChatAgent 使用长期记忆

包含：

- M6 affinity stub
- M7 ChatAgent integration

验收：

- 对话前能召回记忆。
- 对话后能写入候选记忆。
- `love_snapshot` 只作为外部上下文，不由 memory 模块维护。

### Milestone D：可演示、可回归

包含：

- M8 tests/demo

验收：

- demo 展示跨 session 记忆召回。
- 测试覆盖 store / window / retriever / classifier。

## 8. 统一验收场景

### 场景 1：显式记住偏好

输入：

```text
记住，我喜欢你回答短一点。
```

预期：

- 生成 semantic memory。
- scope 为 `preference`。
- 后续 Prompt context 包含“用户喜欢回答简短”。

### 场景 2：短期状态记忆

输入：

```text
我最近因为期末考试压力很大。
```

预期：

- 生成 semantic memory。
- scope 为 `state`。
- 包含 `expires_at`。
- 后续问“我现在该怎么安排复习”时可召回。

### 场景 3：episodic 经验

输入过程：

```text
用户表达焦虑 -> Agent 安抚并拆分计划 -> 用户说感觉好多了
```

预期：

- 生成 episodic memory。
- summary 描述问题、Agent 行动、结果。
- 包含 `love_snapshot`，但不更新权威 `love`。

### 场景 4：用户纠正

输入：

```text
别叫我小王，叫我阿辰。
```

预期：

- 旧昵称相关 semantic 标记为 `superseded`。
- 新偏好写入 semantic。
- 产生 profile candidate。

### 场景 5：模型推断不直接入库

输入：

```text
用户没有明确说偏好，但模型猜测用户喜欢先安慰再建议。
```

预期：

- 不直接写 semantic。
- 生成 `needs_user_confirmation` 候选。
- 可由 ChatAgent 询问：“那我以后记住你更喜欢先听安慰、再听建议，好不好？”

## 9. 开放问题

这些问题不阻塞 MVP，但会影响后续迭代：

- `user_id` 和 `session_id` 最终由 API 层、前端层还是 ChatAgent 调用方传入？
- 是否允许增加 `pytest` 作为开发测试依赖？
- 记忆文件是否需要加密或脱敏？
- 后台管理接口是本期做，还是等 MVP 验证后再做？
- LLM classifier 使用哪个模型，是否需要独立 router model？
- `expires_at` 的默认规则如何定义，例如状态类记忆默认 30 天是否合适？

## 10. Definition of Done

一个任务完成必须满足：

- 模块边界符合本文档，不把别的模块职责混进来。
- 有最小单元测试或 demo 验证。
- 不破坏当前 ChatAgent 基础对话能力。
- 不把真实用户记忆文件提交到仓库。
- `love` 不在 memory 模块中作为权威状态被维护。
