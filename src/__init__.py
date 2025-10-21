# src/__init__.py
"""
農會 RAG 系統
主要模組入口
"""

__version__ = "2.0.0"
__title__ = "農會 RAG 系統"
__description__ = "農會智能客服與知識管理系統"

from . import core
from . import domain
from . import infrastructure
from . import api

__all__ = ["core", "domain", "infrastructure", "api"]
