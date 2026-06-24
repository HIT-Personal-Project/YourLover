import re
from typing import List

class TextUtils:
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """提取关键词"""
        pass
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        return re.sub(r'\s+', ' ', text).strip()
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 500) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
