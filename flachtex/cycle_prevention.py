class CycleException(Exception):
    def __init__(self, path, origin):
        self.path = path
        self.origin = origin

    def __str__(self):
        if self.origin:
            return f"CycleException importing {self.path} ({self.origin})."
        return f"CycleException importing {self.path}."


class CyclePrevention:
    def __init__(self):
        self._checked_paths = set()

    def check(self, path, context=None):
        if path in self._checked_paths:
            raise CycleException(path, context)
        self._checked_paths.add(path)
