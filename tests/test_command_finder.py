import unittest

from flachtex import CommandFinder
from flachtex.command_finder import CommandMatch


class CommandFinderTest(unittest.TestCase):
    def test_empty(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = ""
        self.assertEqual(cf.find(text), None)

    def test_no_match(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a simple string\n bla"
        self.assertEqual(cf.find(text), None)

    def test_no_match2(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todonot{bla} simple string\n bla"
        self.assertEqual(cf.find(text), None)

    def test_2(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todo{bla} simple string\n bla"
        m = cf.find(text)
        self.assertEqual(m, CommandMatch("todo", 10, 20, [(16, 19)], []))
        self.assertEqual(text[m.start:m.end], "\\todo{bla}")

    def test_opt_param(self):
        cf = CommandFinder()
        cf.add_command("todo", 1, 1)
        text = "This is a \\todo{bla} simple string\n bla"
        self.assertEqual(
            cf.find(text), CommandMatch("todo", 10, 20, [(16, 19)], [None])
        )

    def test_hash_param(self):
        cf = CommandFinder()
        cf.add_command("todo", 1, 1)
        text = "This is a \\todo{bla#1} simple string\n bla"
        self.assertEqual(
            cf.find(text), CommandMatch("todo", 10, 22, [(16, 21)], [None])
        )

    def test_newline(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todo{bla\nbla} simple string\n bla"
        self.assertEqual(cf.find(text), CommandMatch("todo", 10, 24, [(16, 23)], []))

    def test_comment(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todo{bla%}\nbla} simple string\n bla"
        self.assertEqual(cf.find(text), CommandMatch("todo", 10, 26, [(16, 25)], []))

    def test_bad(self):
        cf = CommandFinder(strict=True)
        cf.add_command("renewcommand", 2)
        text = "This is a simple string\n bla \\renewcommand\\thesubfigure{(\\alph{subfigure})} asdas"
        self.assertEqual(cf.find(text), None)
