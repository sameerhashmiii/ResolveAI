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
