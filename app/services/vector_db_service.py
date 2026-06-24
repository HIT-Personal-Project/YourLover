import chromadb
from chromadb.config import Settings
from app.core.config import settings

class VectorDBService:
    def __init__(self):
        self.client = chromadb.Client(
            Settings(persist_directory=settings.CHROMA_PATH)
        )
    
    def create_collection(self, name: str):
        """创建集合"""
        return self.client.create_collection(name=name)
    
    def get_collection(self, name: str):
        """获取集合"""
        return self.client.get_collection(name=name)
    
    def add_documents(self, collection_name: str, documents: list, ids: list, metadatas: list = None):
        """添加文档"""
        collection = self.get_collection(collection_name)
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
    
    def query(self, collection_name: str, query_texts: list, n_results: int = 5):
        """查询相似文档"""
        collection = self.get_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            n_results=n_results
        )
