from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"
    DATABASE = "database"
    EXTERNAL = "external"
    FILE = "file"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    CLIENT = "client"


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "code": self.code.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
        }


class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details=details,
            status_code=400,
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found",
            code=ErrorCode.NOT_FOUND,
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.INFO,
            details={"resource": resource, "identifier": str(identifier)},
            status_code=404,
        )


class AlreadyExistsError(AppError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} already exists",
            code=ErrorCode.ALREADY_EXISTS,
            category=ErrorCategory.DUPLICATE,
            severity=ErrorSeverity.WARNING,
            details={"resource": resource, "identifier": str(identifier)},
            status_code=409,
        )


class DatabaseError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.ERROR,
            details=details,
            status_code=500,
        )


class ExternalServiceError(AppError):
    def __init__(
        self, service: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service} error: {message}",
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.ERROR,
            details={"service": service, **(details or {})},
            status_code=502,
        )


class FileProcessingError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.FILE_PROCESSING_ERROR,
            category=ErrorCategory.FILE,
            severity=ErrorSeverity.ERROR,
            details=details,
            status_code=422,
        )


class BadRequestError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.BAD_REQUEST,
            category=ErrorCategory.CLIENT,
            severity=ErrorSeverity.WARNING,
            details=details,
            status_code=400,
        )


def handle_exception(e: Exception) -> tuple[Dict[str, Any], int]:
    if isinstance(e, AppError):
        return e.to_dict(), e.status_code

    return {
        "error": str(e),
        "code": ErrorCode.INTERNAL_ERROR.value,
        "category": ErrorCategory.INTERNAL.value,
        "severity": ErrorSeverity.ERROR.value,
        "details": {"type": type(e).__name__},
    }, 500
