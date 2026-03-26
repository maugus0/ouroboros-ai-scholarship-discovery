"""Custom exception classes for the Scholarship Discovery Agent."""


class ScholarshipDiscoveryBaseError(Exception):
    """Base exception for all Scholarship Discovery Agent errors."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseError(ScholarshipDiscoveryBaseError):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message=message, status_code=500)


class NotFoundError(ScholarshipDiscoveryBaseError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(message=f"{resource} not found", status_code=404)


class ValidationError(ScholarshipDiscoveryBaseError):
    """Raised when request validation fails beyond Pydantic checks."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message=message, status_code=422)


class ServiceAuthError(ScholarshipDiscoveryBaseError):
    """Raised when inter-service authentication fails."""

    def __init__(self, message: str = "Service authentication failed"):
        super().__init__(message=message, status_code=401)


class CrawlError(ScholarshipDiscoveryBaseError):
    """Raised when a web crawl operation fails."""

    def __init__(self, message: str = "Crawl operation failed"):
        super().__init__(message=message, status_code=502)


class LLMExtractionError(ScholarshipDiscoveryBaseError):
    """Raised when LLM extraction fails after retries."""

    def __init__(self, message: str = "LLM extraction failed"):
        super().__init__(message=message, status_code=502)


class LinkingError(ScholarshipDiscoveryBaseError):
    """Raised when scholarship-program linking fails."""

    def __init__(self, message: str = "Scholarship-program linking failed"):
        super().__init__(message=message, status_code=500)


class EligibilityFilterError(ScholarshipDiscoveryBaseError):
    """Raised when eligibility filtering fails."""

    def __init__(self, message: str = "Eligibility filtering failed"):
        super().__init__(message=message, status_code=500)
