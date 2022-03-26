import unittest

from flachtex import FileGuesser
from flachtex.parser import Flattener
from flachtex.rules import NativeIncludeRule, BasicSkipRule, ExplicitImportRule, \
    SubimportRule


class SimpleTest(unittest.TestCase):
    def flatten(self, document, root="main.tex"):
        file_guesser = FileGuesser(document)
        include_rules = [NativeIncludeRule(), ExplicitImportRule(), SubimportRule()]
        skip_rules = [BasicSkipRule()]
        flattener = Flattener(file_guesser=file_guesser, include_rules=include_rules,
                              skip_rules=skip_rules)
        return str(flattener.flatten(root))

    def test_no_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\line 2\nline 3\nline 4\n",
            "sub.tex": "line 2\nline 3\n"
        }
        self.assertEqual(self.flatten(test_document),
                         "line 0\nline 1\n\line 2\nline 3\nline 4\n")

    def test_single_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
            "sub.tex": "line 2\nline 3"
        }
        self.assertEqual(flatten(test_document),
                         "line 0\nline 1\nline 2\nline 3\nline 4\n")

    def test_single_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\nline 3"
        }
        self.assertEqual(self.flatten(test_document),
                         "line 0\nline 1\nline 2\nline 3\nline 4\n")

    def test_relative_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\n\\include{sub2.tex}\n",
            "dir/sub2.tex": "line 3\n",
        }
        self.assertEqual(self.flatten(test_document),
                         "line 0\nline 1\nline 2\nline 3\n\n\nline 4\n")

    def test_skip(self):
        test_document = {
            "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 3\n%%FLACHTEX-SKIP-STOP\nline 5\n"
        }
        self.assertEqual(self.flatten(test_document), "line 0\n\nline 5\n")
