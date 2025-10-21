# src/infrastructure/vector_store.py
"""
向量儲存管理器
負責 Chroma 向量資料庫的初始化、文件添加、搜尋等操作
支援 OpenAI 和 Google Gemini Embeddings
整合 LLMConfig 配置
"""

from typing import List, Dict, Optional
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores.utils import filter_complex_metadata
import json

# ✅ 使用新的配置模組
from ..core.config import LLMConfig


class VectorStoreManager:
    """Chroma 向量資料庫管理器"""
    
    def __init__(self, config, persist_directory: str = None,
                 collection_name: str = None, use_gemini: bool = False):
        """
        初始化向量資料庫管理器
        
        Args:
            config: 配置物件（向後相容）
            persist_directory: 持久化目錄路徑
            collection_name: Collection 名稱
            use_gemini: 是否使用 Gemini Embeddings（預設使用 OpenAI）
        """
        self.config = config
        self.persist_directory = persist_directory or config.CHROMA_PERSIST_DIR
        self.collection_name = collection_name or config.CHROMA_COLLECTION
        
        # ✅ 使用 LLMConfig 初始化 Embeddings
        self._init_embeddings(use_gemini)
        
        self.vectorstore = None
        self.init_vectorstore()
    
    def _init_embeddings(self, use_gemini: bool = False):
        """初始化 Embeddings（使用 LLMConfig）"""
        if use_gemini:
            try:
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",  # ✅ Gemini 正確的模型名稱
                    google_api_key=LLMConfig.GOOGLE_API_KEY
                )
                print("✅ 使用 Google Gemini Embeddings (models/embedding-001)")
            except Exception as e:
                print(f"⚠️ Gemini Embeddings 初始化失敗: {e}")
                print("   切換到 OpenAI Embeddings")
                self.embeddings = OpenAIEmbeddings(
                    model=LLMConfig.OPENAI_EMBEDDING_MODEL,
                    openai_api_key=LLMConfig.OPENAI_API_KEY
                )
                print(f"✅ 使用 OpenAI Embeddings ({LLMConfig.OPENAI_EMBEDDING_MODEL})")
        else:
            self.embeddings = OpenAIEmbeddings(
                model=LLMConfig.OPENAI_EMBEDDING_MODEL,
                openai_api_key=LLMConfig.OPENAI_API_KEY
            )
            print(f"✅ 使用 OpenAI Embeddings ({LLMConfig.OPENAI_EMBEDDING_MODEL})")
    
    def init_vectorstore(self):
        """初始化向量資料庫"""
        try:
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            print(f"✅ Chroma 向量資料庫已初始化 (Collection: {self.collection_name})")
        except Exception as e:
            print(f"❌ Chroma 初始化失敗: {e}")
            raise
    
    def clean_metadata(self, documents: List[Document]) -> List[Document]:
        """
        清理 metadata，確保符合 Chroma 要求
        
        Args:
            documents: 文件列表
            
        Returns:
            List[Document]: 清理後的文件列表
        """
        cleaned_docs = []
        for doc in documents:
            cleaned_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, list):
                    # 列表轉為逗號分隔字串
                    cleaned_metadata[key] = ", ".join(str(v) for v in value) if value else ""
                elif isinstance(value, dict):
                    # 字典轉為 JSON 字串
                    cleaned_metadata[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    # 基本類型直接保留
                    cleaned_metadata[key] = value
                else:
                    # 其他類型轉為字串
                    cleaned_metadata[key] = str(value)
            
            cleaned_doc = Document(
                page_content=doc.page_content,
                metadata=cleaned_metadata
            )
            cleaned_docs.append(cleaned_doc)
        
        return cleaned_docs
    
    def add_documents(self, documents: List[Document], metadatas: List[Dict] = None,
                     ids: List[str] = None) -> List[str]:
        """
        添加文件到向量資料庫
        
        Args:
            documents: 文件列表或文字列表
            metadatas: metadata 列表
            ids: 文件 ID 列表
            
        Returns:
            List[str]: 文件 ID 列表
        """
        try:
            # 如果傳入的是文字列表，轉換為 Document
            if documents and isinstance(documents[0], str):
                docs = [Document(page_content=text, metadata=meta or {})
                       for text, meta in zip(documents, metadatas or [{}] * len(documents))]
            else:
                docs = documents
            
            # 清理 metadata
            cleaned_docs = self.clean_metadata(docs)
            cleaned_docs = filter_complex_metadata(cleaned_docs)
            
            # 添加到向量資料庫
            if ids:
                result_ids = self.vectorstore.add_documents(cleaned_docs, ids=ids)
            else:
                result_ids = self.vectorstore.add_documents(cleaned_docs)
            
            print(f"✅ 已添加 {len(result_ids)} 個文件到向量資料庫")
            
            # 持久化
            self.vectorstore.persist()
            
            return result_ids
            
        except Exception as e:
            print(f"❌ 添加文件失敗: {e}")
            raise
    
    def search(self, query_text: str, n_results: int = 5,
              where: Optional[Dict] = None) -> Dict:
        """
        向量搜尋（相容舊 API）
        
        Args:
            query_text: 查詢文字
            n_results: 返回數量
            where: metadata 過濾條件
            
        Returns:
            Dict: 搜尋結果 {documents: [[]], metadatas: [[]], ids: [[]], distances: [[]]}
        """
        try:
            results = self.similarity_search_with_score(
                query=query_text,
                k=n_results,
                filter=where
            )
            
            # 轉換為相容格式
            return {
                'documents': [[doc.page_content for doc, _ in results]],
                'metadatas': [[doc.metadata for doc, _ in results]],
                'ids': [[doc.metadata.get('id', '') for doc, _ in results]],
                'distances': [[score for _, score in results]]
            }
            
        except Exception as e:
            print(f"❌ 向量搜尋失敗: {e}")
            return {'documents': [[]], 'metadatas': [[]], 'ids': [[]], 'distances': [[]]}
    
    def similarity_search(self, query: str, k: int = 5,
                         filter: Optional[Dict] = None) -> List[Document]:
        """
        相似度搜尋（純向量搜尋）
        
        Args:
            query: 搜尋查詢
            k: 返回數量
            filter: metadata 過濾條件
            
        Returns:
            List[Document]: 文件列表
        """
        try:
            if filter:
                results = self.vectorstore.similarity_search(
                    query=query, k=k, filter=filter
                )
            else:
                results = self.vectorstore.similarity_search(query=query, k=k)
            return results
        except Exception as e:
            print(f"❌ 相似度搜尋失敗: {e}")
            return []
    
    def similarity_search_with_score(self, query: str, k: int = 5,
                                    filter: Optional[Dict] = None) -> List[tuple]:
        """
        相似度搜尋（帶分數）
        
        Args:
            query: 搜尋查詢
            k: 返回數量
            filter: metadata 過濾條件
            
        Returns:
            List[tuple]: (Document, score) 元組列表
        """
        try:
            if filter:
                results = self.vectorstore.similarity_search_with_score(
                    query=query, k=k, filter=filter
                )
            else:
                results = self.vectorstore.similarity_search_with_score(
                    query=query, k=k
                )
            return results
        except Exception as e:
            print(f"❌ 相似度搜尋失敗: {e}")
            return []
    
    def delete_by_ids(self, ids: List[str]):
        """
        根據 ID 刪除文件
        
        Args:
            ids: 文件 ID 列表
        """
        try:
            self.vectorstore.delete(ids=ids)
            print(f"✅ 已刪除 {len(ids)} 個文件")
        except Exception as e:
            print(f"❌ 刪除文件失敗: {e}")
            raise
    
    def delete_by_metadata(self, filter: Dict):
        """
        根據 metadata 刪除文件
        
        Args:
            filter: metadata 過濾條件
        """
        try:
            # Chroma 需要先查詢再刪除
            results = self.vectorstore.get(where=filter)
            if results and 'ids' in results:
                ids = results['ids']
                self.vectorstore.delete(ids=ids)
                print(f"✅ 已刪除 {len(ids)} 個文件（根據 metadata）")
        except Exception as e:
            print(f"❌ 刪除文件失敗: {e}")
            raise
    
    def get_collection_count(self) -> int:
        """
        取得 Collection 中的文件數量
        
        Returns:
            int: 文件數量
        """
        try:
            return self.vectorstore._collection.count()
        except Exception as e:
            print(f"❌ 取得文件數量失敗: {e}")
            return 0
    
    def reset_collection(self):
        """重置 Collection（刪除所有文件）"""
        try:
            self.vectorstore.delete_collection()
            self.init_vectorstore()
            print("✅ Collection 已重置")
        except Exception as e:
            print(f"❌ 重置 Collection 失敗: {e}")
            raise
    
    def get_retriever(self, k: int = 5, filter: Optional[Dict] = None,
                     search_type: str = "similarity"):
        """
        取得檢索器（用於 LangChain）
        
        Args:
            k: 返回數量
            filter: metadata 過濾條件
            search_type: 搜尋類型 (similarity / mmr / similarity_score_threshold)
            
        Returns:
            VectorStoreRetriever: 檢索器
        """
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        
        return self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    
    def get_embedding_info(self) -> dict:
        """
        取得當前 Embedding 資訊
        
        Returns:
            dict: Embedding 資訊
        """
        return {
            "model": LLMConfig.OPENAI_EMBEDDING_MODEL,
            "provider": "openai" if isinstance(self.embeddings, OpenAIEmbeddings) else "gemini",
            "dimension": 1536 if isinstance(self.embeddings, OpenAIEmbeddings) else 768
        }
