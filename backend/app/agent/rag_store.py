"""
RAG 向量存储 - 设计规范检索（使用 PostgreSQL + pgvector）
"""
import os
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class DesignSpecStore:
    """设计规范向量存储（基于 PostgreSQL + pgvector）"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.vector_store = None
        self.specs_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "design_specs"
        )
        
        # PostgreSQL 连接字符串
        # 格式: postgresql://user:password@host:port/database
        self.connection_string = os.getenv(
            "PGVECTOR_CONNECTION_STRING",
            "postgresql://postgres:postgres@localhost:5432/design_agent"
        )
        
        # 初始化时加载文档
        self._load_documents()
    
    def _load_documents(self):
        """加载设计规范文档到向量数据库"""
        if not os.path.exists(self.specs_dir):
            print(f"Warning: Design specs directory not found: {self.specs_dir}")
            return
        
        # 加载所有 markdown 文件
        loader = DirectoryLoader(
            self.specs_dir,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        
        try:
            documents = loader.load()
            
            # 分割文档
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n## ", "\n### ", "\n\n", "\n", " "]
            )
            splits = text_splitter.split_documents(documents)
            
            # 添加元数据（从文件名提取类型）
            for doc in splits:
                filename = os.path.basename(doc.metadata.get("source", ""))
                if "banner" in filename:
                    doc.metadata["type"] = "banner"
                elif "poster" in filename:
                    doc.metadata["type"] = "poster"
                elif "detail_page" in filename:
                    doc.metadata["type"] = "detail_page"
                elif "icon" in filename:
                    doc.metadata["type"] = "icon"
                else:
                    doc.metadata["type"] = "general"
            
            # 创建向量存储（PGVector）
            self.vector_store = PGVector.from_documents(
                documents=splits,
                embedding=self.embeddings,
                collection_name="design_specs",
                connection_string=self.connection_string,
                pre_delete_collection=False  # 不删除已有集合，增量更新
            )
            
            print(f"Loaded {len(splits)} document chunks into pgvector database")
        
        except Exception as e:
            print(f"Error loading documents: {e}")
            print(f"Please ensure PostgreSQL with pgvector extension is running")
            print(f"Connection string: {self.connection_string}")
            # 创建空的向量存储
            self.vector_store = None
    
    def search(
        self,
        query: str,
        requirement_type: str = None,
        k: int = 3
    ) -> List[str]:
        """
        语义检索设计规范
        
        Args:
            query: 查询文本
            requirement_type: 需求类型过滤（banner/poster/detail_page/icon）
            k: 返回结果数量
        
        Returns:
            相关设计规范文本列表
        """
        if not self.vector_store:
            return []
        
        try:
            # 构建过滤条件（pgvector 支持元数据过滤）
            filter_dict = None
            if requirement_type:
                filter_dict = {"type": requirement_type}
            
            # 执行检索
            results = self.vector_store.similarity_search(
                query,
                k=k,
                filter=filter_dict
            )
            
            # 提取文本内容
            specs = [doc.page_content for doc in results]
            return specs
        
        except Exception as e:
            print(f"Error searching specs: {e}")
            return []
    
    def search_by_type(self, requirement_type: str, k: int = 5) -> List[str]:
        """
        按类型获取设计规范
        
        Args:
            requirement_type: 需求类型
            k: 返回结果数量
        
        Returns:
            该类型的设计规范
        """
        return self.search(
            query=f"{requirement_type} 设计规范",
            requirement_type=requirement_type,
            k=k
        )


# 单例
_spec_store_instance = None


def get_spec_store() -> DesignSpecStore:
    """获取设计规范存储单例"""
    global _spec_store_instance
    if _spec_store_instance is None:
        _spec_store_instance = DesignSpecStore()
    return _spec_store_instance
