class AppError(Exception):
    def __init__(self, code, message=""):
        if not isinstance(code, ErrorCode):
            err_msg = f"Invalid error '{code}' with message '{message}' was passed to AppError"
            raise AppError(ErrorCode.ERR_INVALID_ERRCODE, err_msg)
        self.code = code
        self.message = message

        summary = f"[{code.name}] {message}"
        super().__init__(summary)

    def __str__(self):
        return f"[{self.code.name}] {self.message}"

@unique
class ErrorCode(Enum):
    ERR_INVALID_ERRCODE = auto()
    ERR_FEATURE_DISABLED = auto()
    ERR_FEATURE_NOT_FOUND = auto()