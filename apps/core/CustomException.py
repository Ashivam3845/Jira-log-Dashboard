class CustomException(Exception):
    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"[Error {self.error_code}]: {self.message}"
