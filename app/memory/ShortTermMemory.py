'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:43:25
LastEditors: HongJin
LastEditTime: 2026-06-25 11:48:36
'''

from app.memory.BaseMemory import BaseMemory



class ShortTermMemory(BaseMemory):
    def __init__(self):
        self.memory = {}
        
    
