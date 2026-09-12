class ServiceError(Exception):
    status_code = 400
    detail = "Request could not be completed"


class NotFoundError(ServiceError):
    status_code = 404
    detail = "Resource not found"


class ForbiddenError(ServiceError):
    status_code = 403
    detail = "Forbidden"


class AuthenticationError(ServiceError):
    status_code = 401
    detail = "Authentication required"


class InvalidCredentialsError(AuthenticationError):
    detail = "Invalid email or password"


class ConflictError(ServiceError):
    status_code = 409
    detail = "Resource state conflicts with this operation"


class AIConfigurationError(ServiceError):
    status_code = 503
    detail = "AI analysis is not configured for this environment"


class ResponseGenerationError(ServiceError):
    status_code = 502
    detail = "A safe customer response could not be generated"


class UnsafeResponseContentError(ServiceError):
    status_code = 422
    detail = "Response text must not claim an unrecorded action was completed"
