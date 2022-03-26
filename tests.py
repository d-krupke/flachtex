import unittest

from flachtex import flatten, FileGuesser

class SimpleTest(unittest.TestCase):
    def test_no_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\line 2\nline 3\nline 4\n",
            "sub.tex": "line 2\nline 3\n"
        }
        flattened = str(flatten("main.tex", FileGuesser(test_document)))
        self.assertEqual(flattened, "line 0\nline 1\n\line 2\nline 3\nline 4\n")

    def test_single_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\import{sub.tex}\nline 4\n",
            "sub.tex": "line 2\nline 3"
        }
        flattened = str(flatten("main.tex", FileGuesser(test_document)))
        self.assertEqual(flattened, "line 0\nline 1\nline 2\nline 3\nline 4\n")

    def test_single_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\import{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\nline 3"
        }
        flattened = str(flatten("main.tex", FileGuesser(test_document)))
        self.assertEqual(flattened, "line 0\nline 1\nline 2\nline 3\nline 4\n")

    def test_relative_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\import{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\n\\include{sub2.tex}\n",
            "dir/sub2.tex": "line 3\n",
        }
        flattened = str(flatten("main.tex", FileGuesser(test_document)))
        self.assertEqual(flattened, "line 0\nline 1\nline 2\nline 3\n\n\nline 4\n")