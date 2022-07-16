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
        self.assertEqual(cf.find(text), CommandMatch("todo", 10, 21, [(16, 19)], []))

    def test_opt_param(self):
        cf = CommandFinder()
        cf.add_command("todo", 1, 1)
        text = "This is a \\todo{bla} simple string\n bla"
        self.assertEqual(
            cf.find(text), CommandMatch("todo", 10, 21, [(16, 19)], [None])
        )

    def test_newline(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todo{bla\nbla} simple string\n bla"
        self.assertEqual(cf.find(text), CommandMatch("todo", 10, 25, [(16, 23)], []))

    def test_comment(self):
        cf = CommandFinder()
        cf.add_command("todo", 1)
        text = "This is a \\todo{bla%}\nbla} simple string\n bla"
        self.assertEqual(cf.find(text), CommandMatch("todo", 10, 27, [(16, 25)], []))
