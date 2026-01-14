class UnwrapError(Exception):
    """Raised when unwrap() is called on an Err, or unwrap_err() on an Ok."""

    def __init__(self, message: str, value: object):
        self.value = value
        super().__init__(message)


class ChainedError:
    """Error with context chain for tracing error propagation.

    Wraps an original error with additional context about where/why
    the error occurred. Multiple contexts can be chained.

    Args:
        error: The original error or a previous ChainedError.
        context: Description of the context where the error occurred.

    Example:
        >>> err = ChainedError("invalid json", "parsing config")
        >>> str(err)
        'parsing config: invalid json'
        >>> err2 = ChainedError(err, "loading user settings")
        >>> str(err2)
        'loading user settings: parsing config: invalid json'
    """

    __slots__ = ("error", "context")

    def __init__(self, error: object, context: str) -> None:
        self.error = error
        self.context = context

    def __str__(self) -> str:
        return f"{self.context}: {self.error}"

    def __repr__(self) -> str:
        return f"ChainedError({self.error!r}, {self.context!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ChainedError):
            return self.error == other.error and self.context == other.context
        return False

    def root_cause(self) -> object:
        """Get the original error at the bottom of the chain."""
        error = self.error
        while isinstance(error, ChainedError):
            error = error.error
        return error

    def chain(self) -> list[str]:
        """Get the full context chain as a list, from outermost to innermost."""
        contexts = [self.context]
        error = self.error
        while isinstance(error, ChainedError):
            contexts.append(error.context)
            error = error.error
        return contexts
