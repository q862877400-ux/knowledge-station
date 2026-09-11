"""统一异常体系。"""
from __future__ import annotations


class KnowledgeStationError(Exception):
    """基类。"""

    def __init__(self, message: str, code: str = "internal_error"):
        super().__init__(message)
        self.code = code


class ConfigError(KnowledgeStationError):
    def __init__(self, message: str):
        super().__init__(message, code="config_error")


class StorageError(KnowledgeStationError):
    def __init__(self, message: str):
        super().__init__(message, code="storage_error")


class DuplicateDocumentError(KnowledgeStationError):
    def __init__(self, file_hash: str):
        super().__init__(f"文件已存在 (hash={file_hash[:16]}...)", code="duplicate_document")


class ParserError(KnowledgeStationError):
    def __init__(self, message: str):
        super().__init__(message, code="parser_error")


class ParserTimeoutError(ParserError):
    def __init__(self, timeout: int):
        super().__init__(f"Parser 超时 ({timeout}s), 已强制终止")


class RetrievalError(KnowledgeStationError):
    def __init__(self, message: str):
        super().__init__(message, code="retrieval_error")


class VectorEngineOfflineError(KnowledgeStationError):
    def __init__(self):
        super().__init__("语义向量引擎离线", code="vector_engine_offline")


class LLMError(KnowledgeStationError):
    def __init__(self, message: str):
        super().__init__(message, code="llm_error")


class AuthError(KnowledgeStationError):
    def __init__(self):
        super().__init__("缺少或无效的 token", code="unauthorized")
