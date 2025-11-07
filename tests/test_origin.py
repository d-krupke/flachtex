from flachtex import FileFinder
from flachtex.preprocessor import Preprocessor


def flatten(document, root="main.tex"):
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", document)
    preprocessor.file_finder = file_finder
    return preprocessor.expand_file(root), preprocessor.structure


def test_no_import():
    test_document = {
        "main.tex": "line 0\nline 1\nline 2\nline 3\nline 4\n",
    }
    flat, sources = flatten(test_document)
    for path, source in test_document.items():
        assert source == sources[path]["content"]
    assert flat.get_origin_of_line(0, 0) == ("main.tex", 0)
    assert flat.get_origin(0) == ("main.tex", 0)
    assert flat.get_origin_of_line(0, 4) == ("main.tex", 4)
    assert flat.get_origin(4) == ("main.tex", 4)
    assert flat.get_origin_of_line(1, 0) == ("main.tex", 7)
    assert flat.get_origin_of_line(2, 4) == ("main.tex", 18)
    assert flat.get_origin(17) == ("main.tex", 17)


def test_single_import():
    test_document = {
        "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
        "sub.tex": "line 2\nline 3",
    }
    flat, sources = flatten(test_document)
    for path, source in test_document.items():
        assert source == sources[path]["content"]
    assert flat.get_origin_of_line(0, 0) == ("main.tex", 0)
    assert flat.get_origin(0) == ("main.tex", 0)
    assert flat.get_origin_of_line(0, 4) == ("main.tex", 4)
    assert flat.get_origin(4) == ("main.tex", 4)
    assert flat.get_origin_of_line(2, 4) == ("sub.tex", 4)
    assert flat.get_origin(17) == ("sub.tex", 3)


def test_flatten_with_missing_file():
    test_document = {
        "main.tex": "line 0\nline 1\n\\input{sub.tex}\nline 4\n",
    }
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", test_document)
    preprocessor.file_finder = file_finder
    # The \input{sub.tex} command should in this case not be expanded
    flat = preprocessor.expand_file("main.tex")
    assert str(flat) == test_document["main.tex"], (
        "Flattened document should match the original when file is missing"
    )
