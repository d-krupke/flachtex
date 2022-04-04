import typing
import unittest


def compute_row_index(content: str)->typing.List[int]:
    index = [0]
    i = content.find("\n")
    while i>=0:
        index.append(i+1)
        i = content.find("\n",i+1)
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
