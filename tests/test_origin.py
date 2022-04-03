import unittest

from flachtex import FileFinder
from flachtex import expand_file


class OriginTest(unittest.TestCase):
    def flatten(self, document, root="main.tex"):
        file_finder = FileFinder("/", root, document)
        return expand_file(root, file_finder=file_finder)

    def test_no_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\nline 2\nline 3\nline 4\n",
        }
        flat = self.flatten(test_document)
        self.assertEqual(flat.get_origin_of_line(0, 0), ("main.tex", 0))
        self.assertEqual(flat.get_origin(0), ("main.tex", 0))
        self.assertEqual(flat.get_origin_of_line(0, 4), ("main.tex", 4))
        self.assertEqual(flat.get_origin(4), ("main.tex", 4))
        self.assertEqual(flat.get_origin_of_line(1, 0), ("main.tex", 7))
        self.assertEqual(flat.get_origin_of_line(2, 4), ("main.tex", 18))
        self.assertEqual(flat.get_origin(17), ("main.tex", 17))

    def test_single_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
            "sub.tex": "line 2\nline 3"
        }
        flat = self.flatten(test_document)
        self.assertEqual(flat.get_origin_of_line(0, 0), ("main.tex", 0))
        self.assertEqual(flat.get_origin(0), ("main.tex", 0))
        self.assertEqual(flat.get_origin_of_line(0, 4), ("main.tex", 4))
        self.assertEqual(flat.get_origin(4), ("main.tex", 4))
        self.assertEqual(flat.get_origin_of_line(2, 4), ("sub.tex", 4))
        self.assertEqual(flat.get_origin(17), ("sub.tex", 3))

