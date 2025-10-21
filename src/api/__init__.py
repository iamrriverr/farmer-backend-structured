# src/api/__init__.py
"""
API 模組
包含所有 API 路由和中介層
"""

# 匯出 v1 路由
from . import v1
from . import middleware

__all__ = ["v1", "middleware"]
