import typing
import unittest


class Range:
    """
    A simple range (for within a text)
    """

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def intersects(self, other):
        # one begin lies within the other
        if self.start <= other.start < self.end:
            return True
        if other.start <= self.start < self.end:
            return True
        return False

    def __le__(self, other):
        return self.start <= other.start

    def __lt__(self, other):
        return self.start < other.start

    def __len__(self):
        return self.end - self.start

    def __repr__(self):
        return f"[{self.start}:{self.end}]"


def compute_row_index(content: str) -> typing.List[int]:
    index = [0]
    i = content.find("\n")
    while i >= 0:
        index.append(i + 1)
        i = content.find("\n", i + 1)
    return index


class TestRowIndex(unittest.TestCase):
    def test_1(self):
        text = "0\n1\n2\n3\n4\n"
        index = compute_row_index(text)
        for i in text.split("\n"):
            b = text.find(i)
            if i:
                self.assertEqual(index[int(i)], b)
        print(index)

    def test_2(self):
        text = "\n1\n2\n3\n4\n"
        index = compute_row_index(text)
        for i in text.split("\n"):
            b = text.find(i)
            if i:
                self.assertEqual(index[int(i)], b)
        print(index)
