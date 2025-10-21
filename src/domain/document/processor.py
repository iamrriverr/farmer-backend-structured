# src/domain/document/processor.py
"""
文件處理器 (Processor)
負責文件載入、分塊、預覽等處理邏輯
"""

from typing import List, Dict, Optional
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    CSVLoader,
    UnstructuredExcelLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """文件處理類別"""
    
    # 支援的文件格式對應的 Loader
    SUPPORTED_FORMATS = {
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.doc': Docx2txtLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader,
        '.csv': CSVLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
    }
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化處理器
        
        Args:
            chunk_size: 分塊大小
            chunk_overlap: 分塊重疊大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def load_document(self, file_path: str) -> Optional[List[Document]]:
        """
        載入文件
        
        Args:
            file_path: 文件路徑
            
        Returns:
            Optional[List[Document]]: Document 列表，失敗返回 None
        """
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None
            
            extension = path.suffix.lower()
            if extension not in self.SUPPORTED_FORMATS:
                print(f"❌ 不支援的文件格式: {extension}")
                return None
            
            # 選擇對應的 Loader
            loader_class = self.SUPPORTED_FORMATS[extension]
            
            # 特殊處理不同格式
            if extension == '.pdf':
                loader = loader_class(str(path), extract_images=True)
            elif extension in ['.txt', '.csv']:
                loader = loader_class(str(path), encoding='utf-8')
            else:
                loader = loader_class(str(path))
            
            # 載入文件
            documents = loader.load()
            if not documents:
                return None
            
            # 添加基本 metadata
            for doc in documents:
                doc.metadata['source'] = str(path)
                doc.metadata['filename'] = path.name
                doc.metadata['file_type'] = extension.replace('.', '')
            
            return documents
            
        except Exception as e:
            print(f"❌ 載入文件失敗: {e}")
            return None
    
    def split_into_chunks(self, documents: List[Document]) -> List[Document]:
        """
        將文件分割成小塊
        
        Args:
            documents: Document 列表
            
        Returns:
            List[Document]: 分塊後的 Document 列表
        """
        try:
            chunks = self.splitter.split_documents(documents)
            
            # 為每個 chunk 添加編號
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['chunk_total'] = len(chunks)
            
            return chunks
            
        except Exception as e:
            print(f"❌ 分塊失敗: {e}")
            return []
    
    def load_and_split(self, file_path: str) -> Optional[List[Document]]:
        """
        載入並分塊（一步到位）
        
        Args:
            file_path: 文件路徑
            
        Returns:
            Optional[List[Document]]: 分塊後的 Document 列表
        """
        documents = self.load_document(file_path)
        if not documents:
            return None
        
        chunks = self.split_into_chunks(documents)
        return chunks if chunks else None
    
    def get_preview(self, file_path: str, max_length: int = 500) -> str:
        """
        取得文件內容預覽
        
        Args:
            file_path: 文件路徑
            max_length: 最大預覽長度
            
        Returns:
            str: 預覽內容
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return "文件不存在"
            
            # 只支援純文字格式的預覽
            if path.suffix in ['.txt', '.md']:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read(max_length)
                    if len(content) == max_length:
                        content += "..."
                    return content
            else:
                return "此文件類型不支援預覽"
                
        except Exception as e:
            return f"預覽失敗: {str(e)}"
    
    def validate_file(self, file_path: str) -> tuple[bool, str]:
        """
        驗證文件是否可以載入
        
        Args:
            file_path: 文件路徑
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, f"文件不存在: {file_path}"
        
        if not path.is_file():
            return False, f"不是文件: {file_path}"
        
        file_size = path.stat().st_size
        max_size = 100 * 1024 * 1024  # 100 MB
        if file_size > max_size:
            return False, f"文件過大: {round(file_size / 1024 / 1024, 2)} MB (最大 100 MB)"
        
        extension = path.suffix.lower()
        if extension not in self.SUPPORTED_FORMATS:
            return False, f"不支援的格式: {extension}"
        
        try:
            with open(path, 'rb') as f:
                f.read(1)
        except Exception as e:
            return False, f"文件無法讀取: {str(e)}"
        
        return True, "文件驗證通過"
