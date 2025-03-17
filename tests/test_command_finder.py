from flachtex import CommandFinder
from flachtex.command_finder import CommandMatch


def test_empty():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = ""
    assert cf.find(text) is None


def test_no_match():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = "This is a simple string\n bla"
    assert cf.find(text) is None


def test_no_match2():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = "This is a \\todonot{bla} simple string\n bla"
    assert cf.find(text) is None


def test_valid_command():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = "This is a \\todo{bla} simple string\n bla"
    m = cf.find(text)
    assert m == CommandMatch("todo", 10, 20, [(16, 19)], [])
    assert text[m.start : m.end] == "\\todo{bla}"


def test_optional_param():
    cf = CommandFinder()
    cf.add_command("todo", 1, 1)
    text = "This is a \\todo{bla} simple string\n bla"
    assert cf.find(text) == CommandMatch("todo", 10, 20, [(16, 19)], [None])


def test_hash_param():
    cf = CommandFinder()
    cf.add_command("todo", 1, 1)
    text = "This is a \\todo{bla#1} simple string\n bla"
    assert cf.find(text) == CommandMatch("todo", 10, 22, [(16, 21)], [None])


def test_newline_in_param():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = "This is a \\todo{bla\nbla} simple string\n bla"
    assert cf.find(text) == CommandMatch("todo", 10, 24, [(16, 23)], [])


def test_comment_in_param():
    cf = CommandFinder()
    cf.add_command("todo", 1)
    text = "This is a \\todo{bla%}\nbla} simple string\n bla"
    assert cf.find(text) == CommandMatch("todo", 10, 26, [(16, 25)], [])


def test_strict_mode_bad_command():
    cf = CommandFinder(strict=True)
    cf.add_command("renewcommand", 2)
    text = "This is a simple string\n bla \\renewcommand\\thesubfigure{(\\alph{subfigure})} asdas"
    assert cf.find(text) is None
