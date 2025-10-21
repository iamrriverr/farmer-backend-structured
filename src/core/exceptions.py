# src/core/exceptions.py
"""
自定義異常類別
統一管理業務邏輯異常
"""

from fastapi import status


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


class ResourceNotFoundException(BusinessException):
    """資源不存在異常"""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} 不存在"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND")


class UnauthorizedException(BusinessException):
    """未授權異常"""
    def __init__(self, message: str = "未授權存取"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED")


class ForbiddenException(BusinessException):
    """禁止存取異常"""
    def __init__(self, message: str = "沒有權限執行此操作"):
        super().__init__(message, status.HTTP_403_FORBIDDEN, "FORBIDDEN")


class ValidationException(BusinessException):
    """驗證異常"""
    def __init__(self, message: str, field: str = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message, status.HTTP_400_BAD_REQUEST, error_code)


class DuplicateResourceException(BusinessException):
    """資源重複異常"""
    def __init__(self, resource: str, field: str = None):
        message = f"{resource} 已存在"
        if field:
            message += f" ({field})"
        super().__init__(message, status.HTTP_409_CONFLICT, "DUPLICATE_RESOURCE")


class ServiceUnavailableException(BusinessException):
    """服務不可用異常"""
    def __init__(self, service: str = "服務"):
        super().__init__(
            f"{service}暫時不可用，請稍後再試",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SERVICE_UNAVAILABLE"
        )
