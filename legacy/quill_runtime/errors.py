class QuillError(Exception):
    """Any lexing, parsing or runtime error raised while running Quill code."""

    def __init__(self, message: str, file: str | None = None, line: int | None = None):
        self.message = message
        self.file = file
        self.line = line
        where = ""
        if file:
            where = f"{file}:{line}: " if line else f"{file}: "
        super().__init__(f"quill: {where}{message}")
