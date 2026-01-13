class UnwrapError(Exception):
    """Raised when unwrap() is called on an Err, or unwrap_err() on an Ok."""

    def __init__(self, message: str, value: object):
        self.value = value
        super().__init__(message)
