"""
配置管理模块
负责：
- 加载和管理应用配置（模型、API、Prompt、Agent、声音、快捷键等）
- 提供配置的读写接口
- 配置变更通知
- 默认配置管理
"""

class Settings():
    APP_NAME: str = "校园情感陪伴助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CHAT_MODEL_NAME = "qwen3-vl:4b" #聊天模型
    EMBEDDING_MODEL_NAME = "qwen3-embedding:4b" #向量化模型
    ROUTER_MODEL_NAME = "qwen2.5:3b" #REACT路由判断模型
    # DATABASE_URL: str = "sqlite:///./data/sqlite/example_db.sqlite3"
    RAG_DATABASE="chroma" #RAG数据库
    CHROMA_PATH: str = "./data/chroma" #RAG数据库本地存储路径文件夹
    # REDIS_URL: str = "redis://localhost:6379/0"
    # LLM_API_KEY: str = ""
    # LLM_MODEL: str = "qwen-plus"
    # VOICE_SERVICE: str = "edge-tts"

    CHUNK_SIZE: int = 1024 #RAG数据库中每个文本段的最大字符数
    CHUNK_OVERLAP: int = 256 #RAG数据库中每个文本段之间的字符串重叠数量
    MAX_SPLIT_CHAR_NUMBER: int = 1024 #RAG数据库中每个文本段的最大字符数量
    RAG_N_RESULTS: int = 20 #RAG数据库中查询结果的数量
    RAG_FILE_UPLOADER: str= "HongJin"
    SEPARATORS: list = [
        # === 1. 结构化标题标记（最高优先级，保留文档层级）===
        "\n# ",       # Markdown H1
        "\n## ",      # Markdown H2
        "\n### ",     # Markdown H3
        "\n#### ",    # Markdown H4
        "\n第",       # 中文"第X章/节"前缀（需配合正则使用更佳）
        "\nChapter ", # 英文章节标记

        # === 2. 段落级分隔（保持段落语义完整）===
        "\n\n",       # 双换行（中英文通用段落分隔）
        "\r\n\r\n",   # Windows 风格双换行

        # === 3. 句子级分隔（中英文句号优先）===
        "。",         # 中文句号
        ". ",         # 英文句号+空格（避免误切小数点/版本号）
        "！",         # 中文感叹号
        "! ",         # 英文感叹号
        "？",         # 中文问号
        "? ",         # 英文问号

        # === 4. 从句/短语级分隔（长句兜底）===
        # "；",         # 中文分号
        # "; ",         # 英文分号
        # "，",         # 中文逗号
        # ", ",         # 英文逗号

        # === 5. 特殊内容分隔 ===
        "\n---\n",    # Markdown 水平线 / 文档分割符
        "\n***\n",    # Markdown 水平线变体
        "\t",         # Tab（表格/列表项分隔）
        " ",          # 空格（最终兜底，仅在其他所有分隔符都超chunk_size时触发）
    ]#RAG数据库中每个文本段的分隔符

    MD5_PATH: str = "./data/md5.txt" #RAG数据库中每个文本段的md5值文件



    TEST_SYSTEM_PROMPT: str = """你是一个温柔、善解人意的情感陪伴助手。请用温暖、关怀的语言回应用户。
        注意用户的情感状态，根据用户的情绪给予适当的安慰和鼓励。"""



settings = Settings()