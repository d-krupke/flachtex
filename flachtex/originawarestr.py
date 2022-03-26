class OriginAwareString:
    """
    An inefficient implementation of an annotated string that keeps track of the characters origins.
    """
    def __init__(self, content: str, origin, offset=0, next=None):
        self._offset = offset
        self._origin = origin
        self._content = content
        self._next = next

    def copy(self):
        next = None if self._next is None else self._next.copy()
        return OriginAwareString(content=self._content,
                                 origin=self._origin,
                                 offset=self._offset,
                                 next=next)

    def get_origin(self, n):
        if n >= len(self._content):
            if self._next is None:
                raise KeyError()
            return self._next.get_origin(n - len(self._content))
        return self._offset + n, self._origin

    def skip(self, n):
        if n == len(self._content):
            return None
        if n > len(self._content):
            return self._next.skip(n - len(self._content))
        return OriginAwareString(content=self._content[n:],
                                 origin=self._origin,
                                 offset=self._offset + n,
                                 next=self._next)

    def cutoff_after(self, n):
        if n > len(self._content):
            self.next = self._next.cutoff_after(n - len(self._content))
        else:
            self._content = self._content[:n]
            self._next = None
        return self

    def __len__(self):
        if self._next is not None:
            return len(self._next) + len(self._content)
        else:
            return len(self._content)

    def append(self, item):
        if self._next is None:
            self._next = item
        else:
            self._next.append(item)
        return self

    def __str__(self):
        if not self._next:
            return self._content
        else:
            return self._content + str(self._next)

    def __getitem__(self, item):
        if isinstance(item, slice):
            l = len(self)
            stop = item.stop
            start = item.start
            if stop is None:
                stop = l
            if start is None:
                start = 0
            if start < 0:
                start = l - start
            if stop < 0:
                stop = l - stop
            x = self.skip(start).copy()
            return x.cutoff_after(stop - start)
        else:
            if item < len(self._origin):
                return self._origin[item]
            else:
                if not self._next:
                    raise KeyError()
                return self._next(item - len(self._content))

    def __add__(self, other):
        return self.copy().append(other.copy())
