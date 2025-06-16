from flachtex import FileFinder, Preprocessor, remove_comments
from flachtex.rules import SubimportChangesRule


def flatten(document, root="main.tex", comments=False):
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", document)
    preprocessor.file_finder = file_finder
    preprocessor.subimport_rules.append(SubimportChangesRule())
    doc = preprocessor.expand_file(root)
    if comments:
        doc = remove_comments(doc)
    return str(doc)


def test_no_import():
    document = {
        "main.tex": "line 0\nline 1\n\\line 2\nline 3\nline 4\n",
        "sub.tex": "line 2\nline 3\n",
    }
    assert flatten(document) == "line 0\nline 1\n\\line 2\nline 3\nline 4\n"


def test_single_import():
    document = {
        "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
        "sub.tex": "line 2\nline 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_two_imports():
    document = {
        "main.tex": "line 0\nline 1\n\\input{sub.tex}\n\\input{sub2.tex}\nline 4\n",
        "sub.tex": "line 2\n",
        "sub2.tex": "line 3\n",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\n\nline 3\n\nline 4\n"


def test_single_import_with_linebreak():
    document = {
        "main.tex": "line 0\nline 1\n\\input{\nsub.tex\n}\nline 4\n",
        "sub.tex": "line 2\nline 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_import_from_subfolder():
    document = {
        "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
        "dir/sub.tex": "line 2\nline 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_relative_import_with_subfolder():
    document = {
        "main.tex": "line 0\nline 1\n\\input{dir/sub.tex}\nline 4\n",
        "dir/sub.tex": "line 2\n\\include{sub2.tex}\n",
        "dir/sub2.tex": "line 3\n",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\n\n\nline 4\n"


def test_subimport():
    document = {
        "main.tex": "line 0\nline 1\n\\subimport{dir}{sub}\nline 4\n",
        "dir/sub.tex": "line 2\nline 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_multiple_subimports():
    document = {
        "main.tex": "line 0\nline 1\n\\subimport{dir}{sub}\n\\subimport{dir}{sub2}\nline 4\n",
        "dir/sub.tex": "line 2",
        "dir/sub2.tex": "line 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_subimport_with_star():
    document = {
        "main.tex": "line 0\nline 1\n\\subimport*{dir}{sub}\nline 4\n",
        "dir/sub.tex": "line 2\nline 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_multiple_subimports_with_star():
    document = {
        "main.tex": "line 0\nline 1\n\\subimport*{dir}{sub}\n\\subimport*{dir}{sub2}\nline 4\n",
        "dir/sub.tex": "line 2",
        "dir/sub2.tex": "line 3",
    }
    assert flatten(document) == "line 0\nline 1\nline 2\nline 3\nline 4\n"


def test_skip_functionality():
    document = {
        "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 3\n%%FLACHTEX-SKIP-STOP\nline 5\n"
    }
    assert flatten(document) == "line 0\n\nline 5\n"


def test_multiple_skip_blocks():
    document = {
        "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 3\n%%FLACHTEX-SKIP-STOP\n%%FLACHTEX-SKIP-START\nbla\n%%FLACHTEX-SKIP-STOP\nline 5\n"
    }
    assert flatten(document) == "line 0\n\n\nline 5\n"


def test_comment_package():
    document = {
        "main.tex": "line 0\nline 1\n\\begin{comment}\nline 2\n\\end{comment}\nline 3\n",
    }
    assert flatten(document, comments=True) == "line 0\nline 1\nline 3\n"


def test_comment_package_double():
    document = {
        "main.tex": "line 0\nline 1\n\\begin{comment}\nline 2\n\\end{comment}\nline 3\n\\begin{comment}\nline 4\n\\end{comment}\nline 5\n",
    }
    assert flatten(document, comments=True) == "line 0\nline 1\nline 3\nline 5\n"


def test_comment_package_double_space_and_tab():
    document = {
        "main.tex": "line 0\nline 1\n\t\\begin{comment}\nline 2\n\t\\end{comment}\nline 3\n  \\begin{comment}\nline 4\n  \\end{comment}\nline 5\n",
    }
    assert flatten(document, comments=True) == "line 0\nline 1\nline 3\nline 5\n"


def test_complex_subimports():
    document = {
        "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n\\subimport{subimport}{subimport.tex}\nline 10\n",
        "sub.tex": "line 2\nline 3",
        "subimport/subimport.tex": "line 5\n\\includegraphics{1.pdf}\n\\includegraphics{/2.pdf}\n\\includegraphics{./3.pdf}\nline 6\n\\include{./subimportb.tex}\nline 9\n",
        "subimport/subimportb.tex": "line 7\n\\includegraphics{4.pdf}\nline 8\n",
    }
    assert flatten(document) == (
        "line 0\nline 1\nline 2\nline 3\nline 4\n"
        "line 5\n\\includegraphics{./subimport/1.pdf}\n\\includegraphics{./subimport/2.pdf}\n\\includegraphics{./subimport/3.pdf}\nline 6\n"
        "line 7\n\\includegraphics{./subimport/4.pdf}\nline 8\n\nline 9\n"
        "\nline 10\n"
    )
