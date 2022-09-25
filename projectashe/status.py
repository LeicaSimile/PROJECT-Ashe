from enum import Enum

class CommandStatus(Enum):
    """
    Attributes:
        FAILED: Generic failure status.
        COMPLETED: Command was successfully completed.
        CANCELLED: Command either timed out or was interrupted/cancelled.
        INVALID: Couldn't proceed due to invalid user permissions or input.
        FORBIDDEN: Bot doesn't have permission to proceed with command execution.

    """
    FAILED = 0
    COMPLETED = 1
    CANCELLED = 2
    INVALID = 3
    FORBIDDEN = 4
