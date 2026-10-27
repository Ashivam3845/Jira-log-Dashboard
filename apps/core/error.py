"""Custom error handling with enhanced logging and traceback."""

import inspect
import traceback
from typing import Optional, Union

from apps.core.logger import logger


class CustomError(Exception):
    def __init__(self, error: Union[str, Exception], status_code: int = 500):
        self.status_code = status_code

        if isinstance(error, Exception):
            self.message = str(error)
            self.trace = traceback.format_exc()
        elif isinstance(error, str):
            self.message = error
            self.trace = None
        else:
            raise CustomError(f"Unknown Error type: {error}", status_code=status_code)

        self.raised_from = self._get_calling_function()
        self._log_error()
        super().__init__(self.message)

    def _get_calling_function(self) -> Optional[str]:
        """Get the function name from where the exception was raised."""
        stack = inspect.stack()
        for frame in stack[2:]:
            module = inspect.getmodule(frame[0])
            if module and module.__name__ != __name__:
                return f"{module.__name__}.{frame.function}()"
        return f"{stack[2].function}()" if len(stack) > 2 else "unknown"

    def _log_error(self):
        """Central error logging with traceback and function context."""
        if self.trace:
            logger.error(
                f" Exception in {self.raised_from}: Message: {self.message} Traceback: {self.trace}"
            )
        else:
            logger.error(f"Error in {self.raised_from}: Message: {self.message}")

    def to_dict(self):
        return {
            "error": self.message,
            "status_code": self.status_code,
            "trace": self.trace,
        }
