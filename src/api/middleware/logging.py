# src/api/middleware/logging.py
"""
日誌記錄中介層
記錄所有 API 請求、回應時間、錯誤等
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from datetime import datetime
from typing import Callable
import json


# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    請求日誌記錄中介層
    
    記錄每個 API 請求的詳細資訊
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        處理請求並記錄
        
        Args:
            request: 請求物件
            call_next: 下一個處理器
            
        Returns:
            Response: 回應物件
        """
        # 開始計時
        start_time = time.time()
        
        # 提取請求資訊
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        
        # 記錄請求開始
        logger.info(f"➡️  [{method}] {url} - Client: {client_host}")
        
        # 處理請求
        try:
            response = await call_next(request)
            
            # 計算處理時間
            process_time = time.time() - start_time
            
            # 記錄回應
            status_code = response.status_code
            log_message = (
                f"⬅️  [{method}] {url} - "
                f"Status: {status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            if status_code >= 500:
                logger.error(log_message)
            elif status_code >= 400:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # 添加處理時間到回應 header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 記錄錯誤
            process_time = time.time() - start_time
            logger.error(
                f"❌ [{method}] {url} - "
                f"Error: {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise


class DetailedRequestLogger:
    """
    詳細請求日誌記錄器
    
    用於記錄特定端點的詳細資訊（可選用）
    """
    
    @staticmethod
    async def log_request_body(request: Request):
        """
        記錄請求 body
        
        Args:
            request: 請求物件
        """
        try:
            body = await request.body()
            if body:
                # 嘗試解析 JSON
                try:
                    body_json = json.loads(body)
                    logger.debug(f"Request Body: {json.dumps(body_json, ensure_ascii=False)}")
                except:
                    logger.debug(f"Request Body: {body.decode('utf-8')[:500]}")
        except Exception as e:
            logger.warning(f"無法記錄請求 body: {e}")
    
    @staticmethod
    def log_user_action(user_id: int, action: str, details: dict = None):
        """
        記錄用戶操作
        
        Args:
            user_id: 用戶 ID
            action: 操作類型
            details: 詳細資訊
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
        logger.info(f"用戶操作: {json.dumps(log_data, ensure_ascii=False)}")


def setup_logging_middleware(app):
    """
    註冊日誌中介層到 FastAPI 應用
    
    Args:
        app: FastAPI 應用實例
    """
    app.add_middleware(RequestLoggingMiddleware)
    print("✅ 日誌中介層已註冊")
