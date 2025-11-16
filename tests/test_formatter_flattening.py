"""
Tests for formatter with flattening to identify issues.
"""

from flachtex import FileFinder, Preprocessor
from flachtex.formatter import format_latex


def test_simple_flatten_then_format():
    """Test basic flattening followed by formatting."""
    documents = {
        "main.tex": "This is main. \\input{sub.tex} End of main.",
        "sub.tex": "This is sub. More sub.",
    }
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", documents)
    preprocessor.file_finder = file_finder
    doc = preprocessor.expand_file("main.tex")

    print("\n=== After flattening ===")
    print(repr(str(doc)))
    print(f"Type: {type(doc)}")
    print(f"Origins: {doc.origins}")

    result = format_latex(doc, indent=2)

    print("\n=== After formatting ===")
    print(repr(str(result)))
    print(f"Type: {type(result)}")

    # Should have all content
    assert "This is main." in str(result)
    assert "This is sub." in str(result)
    assert "End of main." in str(result)


def test_flatten_with_environment_then_format():
    """Test flattening with environments followed by formatting."""
    documents = {
        "main.tex": ("Before include.\n\\input{sub.tex}\nAfter include."),
        "sub.tex": ("\\begin{itemize}\n\\item First item.\n\\end{itemize}"),
    }
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", documents)
    preprocessor.file_finder = file_finder
    doc = preprocessor.expand_file("main.tex")

    print("\n=== After flattening ===")
    print(repr(str(doc)))

    result = format_latex(doc, indent=2)

    print("\n=== After formatting ===")
    print(repr(str(result)))

    # Should have indented environment
    assert "\\begin{itemize}" in str(result)
    assert "\\item First item." in str(result)
    assert "Before include." in str(result)
    assert "After include." in str(result)


def test_nested_includes_with_format():
    """Test nested includes with formatting."""
    documents = {
        "main.tex": "Main text. \\input{level1.tex} End main.",
        "level1.tex": "Level 1. \\input{level2.tex} End level 1.",
        "level2.tex": "Level 2 text.",
    }
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", documents)
    preprocessor.file_finder = file_finder
    doc = preprocessor.expand_file("main.tex")

    print("\n=== After flattening (nested) ===")
    print(repr(str(doc)))

    result = format_latex(doc, indent=2)

    print("\n=== After formatting (nested) ===")
    print(repr(str(result)))

    # Should have all content
    assert "Main text." in str(result)
    assert "Level 1." in str(result)
    assert "Level 2 text." in str(result)


def test_flatten_multiline_with_format():
    """Test flattening multi-line content with formatting."""
    documents = {
        "main.tex": (
            "First sentence in main. Second sentence in main.\n"
            "\\input{sub.tex}\n"
            "Third sentence in main."
        ),
        "sub.tex": (
            "First sentence in sub. Second sentence in sub.\nThird sentence in sub."
        ),
    }
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", documents)
    preprocessor.file_finder = file_finder
    doc = preprocessor.expand_file("main.tex")

    print("\n=== After flattening (multiline) ===")
    print(repr(str(doc)))
    print(f"Length: {len(str(doc))}")

    result = format_latex(doc, indent=0, sentence_per_line=True)

    print("\n=== After formatting (multiline) ===")
    print(repr(str(result)))
    print(f"Length: {len(str(result))}")

    result_str = str(result)

    # Each sentence should be on its own line
    assert "First sentence in main.\n" in result_str
    assert "Second sentence in main.\n" in result_str
    assert "First sentence in sub.\n" in result_str
    assert "Second sentence in sub.\n" in result_str
    assert "Third sentence in sub.\n" in result_str
    assert "Third sentence in main." in result_str
