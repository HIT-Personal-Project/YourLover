

from app.memory.BaseMemory import BaseMemory


class LongTermMemory(BaseMemory):
    def __init__(self):
        self.memory = {}