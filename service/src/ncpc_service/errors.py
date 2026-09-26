class NcpcError(Exception):
    code = "NCPC_ERROR"
    status_code = 400


class NotFoundError(NcpcError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(NcpcError):
    code = "CONFLICT"
    status_code = 409


class AuthorizationError(NcpcError):
    code = "FORBIDDEN"
    status_code = 403


class AuthenticationError(NcpcError):
    code = "UNAUTHORIZED"
    status_code = 401


class InvalidTransitionError(NcpcError):
    code = "INVALID_TRANSITION"
    status_code = 409


class RateLimitError(NcpcError):
    code = "RATE_LIMITED"
    status_code = 429


class RequestTooLargeError(NcpcError):
    code = "REQUEST_TOO_LARGE"
    status_code = 413
