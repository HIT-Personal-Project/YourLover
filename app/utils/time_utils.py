from datetime import datetime, timedelta

class TimeUtils:
    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        return datetime.now().isoformat()
    
    @staticmethod
    def get_today() -> datetime:
        """获取今天"""
        return datetime.now().date()
    
    @staticmethod
    def is_morning() -> bool:
        """判断是否上午"""
        return 6 <= datetime.now().hour < 12
    
    @staticmethod
    def is_evening() -> bool:
        """判断是否晚上"""
        return datetime.now().hour >= 18
    
    @staticmethod
    def get_days_ago(days: int) -> datetime:
        """获取几天前的日期"""
        return datetime.now() - timedelta(days=days)
