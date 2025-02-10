class SDKError(Exception):
    """Base class for all SDK errors"""

class UserError(SDKError):
    """Exception raised for user-related errors"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class InvalidInputsError(UserError):
    """Exception raised for invalid inputs"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class APIError(SDKError):
    """Exception raised for API-returned errors. Should be handled to be more specific"""
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ProtocolError(SDKError):
    """Exception raised for protocol-related errors"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

