# src/api/middleware/error_handler.py
"""
全域錯誤處理中介層
統一處理各種異常並返回標準化的錯誤回應
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from datetime import datetime


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    處理 HTTP 異常
    
    Args:
        request: 請求物件
        exc: HTTP 異常
        
    Returns:
        JSONResponse: 錯誤回應
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    處理請求驗證錯誤
    
    Args:
        request: 請求物件
        exc: 驗證錯誤
        
    Returns:
        JSONResponse: 錯誤回應
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "請求資料驗證失敗",
                "details": errors,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    處理所有未捕獲的異常
    
    Args:
        request: 請求物件
        exc: 異常
        
    Returns:
        JSONResponse: 錯誤回應
    """
    # 記錄完整的錯誤堆疊
    error_trace = traceback.format_exc()
    print(f"❌ 未預期的錯誤: {error_trace}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "伺服器內部錯誤，請稍後再試",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


class BusinessException(Exception):
    """
    業務邏輯異常基類
    
    用於 Service 層拋出特定的業務錯誤
    """
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """
    處理業務邏輯異常
    
    Args:
        request: 請求物件
        exc: 業務異常
        
    Returns:
        JSONResponse: 錯誤回應
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "BusinessException",
                "message": exc.message,
                "code": exc.error_code,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


def setup_exception_handlers(app):
    """
    註冊所有異常處理器到 FastAPI 應用
    
    Args:
        app: FastAPI 應用實例
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    print("✅ 異常處理器已註冊")
