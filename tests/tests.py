import unittest

from flachtex import FileFinder, expand_file


class SimpleTest(unittest.TestCase):
    def flatten(self, document, root="main.tex"):
        file_finder = FileFinder("/", root, document)
        return str(expand_file(root, file_finder=file_finder))

    def test_no_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\line 2\nline 3\nline 4\n",
            "sub.tex": "line 2\nline 3\n",
        }
        assert (
            self.flatten(test_document) == "line 0\nline 1\n\\line 2\nline 3\nline 4\n"
        )

    def test_single_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
            "sub.tex": "line 2\nline 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_two_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{sub.tex}\n\\input{sub2.tex}\nline 4\n",
            "sub.tex": "line 2\n",
            "sub2.tex": "line 3\n",
        }
        assert (
            self.flatten(test_document)
            == "line 0\nline 1\nline 2\n\nline 3\n\nline 4\n"
        )

    def test_single_import_linebreak(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{\nsub.tex\n}\nline 4\n",
            "sub.tex": "line 2\nline 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_single_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\nline 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_relative_subfolder_import(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
            "dir/sub.tex": "line 2\n\\include{sub2.tex}\n",
            "dir/sub2.tex": "line 3\n",
        }
        assert (
            self.flatten(test_document)
            == "line 0\nline 1\nline 2\nline 3\n\n\nline 4\n"
        )

    def test_subimport(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\subimport{dir}{sub}\nline 4\n",
            "dir/sub.tex": "line 2\nline 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_subimport2(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\subimport{dir}{sub}\n\\subimport{dir}{sub2}\nline 4\n",
            "dir/sub.tex": "line 2",
            "dir/sub2.tex": "line 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_subimportstar(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\subimport*{dir}{sub}\nline 4\n",
            "dir/sub.tex": "line 2\nline 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_subimportstar2(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\subimport*{dir}{sub}\n\\subimport*{dir}{sub2}\nline 4\n",
            "dir/sub.tex": "line 2",
            "dir/sub2.tex": "line 3",
        }
        assert self.flatten(test_document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"

    def test_skip(self):
        test_document = {
            "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 3\n%%FLACHTEX-SKIP-STOP\nline 5\n"
        }
        assert self.flatten(test_document) == "line 0\n\nline 5\n"

    def test_skip2(self):
        test_document = {
            "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 3\n%%FLACHTEX-SKIP-STOP\n%%FLACHTEX-SKIP-START\nbla\n%%FLACHTEX-SKIP-STOP\nline 5\n"
        }
        assert self.flatten(test_document) == "line 0\n\n\nline 5\n"

    def test_subimport(self):
        test_document = {
            "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n\\subimport{subimport}{subimport.tex}\nline 10\n",
            "sub.tex": "line 2\nline 3",
            "subimport/subimport.tex": "line 5\n\\includegraphics{1.pdf}\n\\includegraphics{/2.pdf}\n\\includegraphics{./3.pdf}\nline 6\n\\include{./subimportb.tex}\nline 9\n",
            "subimport/subimpoetb.tex": "line7\n\\includegraphics{4.pdf}\nline8\n"
        }
        assert self.flatten(test_document) == ("line 0\nline 1\nline 2\nline 3\nline 4\n"
                                               "line 5\n\\includegraphics{./subimport/1.pdf}\n\\includegraphics{./subimport/2.pdf}\n\\includegraphics{./subimport/3.pdf}\nline 6\n"
                                               "line7\n\\includegraphics{./subimport/4.pdf}\nline8\n\nline 9\n"
                                               "\nline 10\n")
