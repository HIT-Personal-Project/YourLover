"""长期记忆模块。

提供情感陪伴 Agent 的长期记忆能力，包括：
    - schema: 三类记忆（语义/情节/程序性候选）的数据模型
    - store: 基于文件的用户记忆持久化
    - retriever: 基于关键词 + 重要性 + 时序的轻量检索
    - classifier: 基于规则的记忆候选提取
    - window: 短期对话窗口裁剪
    - MemoryItem / EmotionMemory: 兼容历史视图与运行时状态
    - profile_candidate: 用户画像更新候选
"""
