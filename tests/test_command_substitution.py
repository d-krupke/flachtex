import unittest

from flachtex import CommandFinder, TraceableString
from flachtex.command_finder import CommandMatch
from flachtex.command_substitution import (
    find_new_commands,
    NewCommandSubstitution,
    NewCommandDefinition,
)
from flachtex.rules import apply_substitution_rules

doc1 = TraceableString(
    r"""
\newcommand{\MSClength}{MSC-MS\xspace}
\newcommand{\MSCtotEnergy}{MSC-TE\xspace}
\newcommand{\MSClocEnergy}{MSC-BE\xspace}

\newcommand{\MIPone}{MIP-1\xspace}
\newcommand{\MIPtwo}{MIP-2\xspace}
\newcommand{\MIPthree}{MIP-3\xspace}
\newcommand{\CPone}{CP-1\xspace}
\newcommand{\CPtwo}{CP-2\xspace}

\newcommand{\cone}{cone\xspace}\newcommand{\cupdot}{\mathbin{\mathaccent\cdot\cup}}
\newcommand{\mincover}{$\Lambda$-cover\xspace}

\MIPone
""",
    "main.tex",
)


class CommandSubstitutionTest(unittest.TestCase):
    def test_empty(self):
        cmds = list(find_new_commands(TraceableString("", "Main.tex")))
        self.assertListEqual(cmds, [])

    def test_doc1(self):
        cmds = list(find_new_commands(doc1))
        self.assertEqual(len(cmds), 11)
        sub = NewCommandSubstitution()
        for cmd in cmds:
            sub.new_command(
                NewCommandDefinition(cmd.name, cmd.num_parameters, cmd.command)
            )
        replacements = list(sub.find_all(doc1))
        self.assertEqual(len(replacements), 1)

    def test2(self):
        sub = NewCommandSubstitution()
        sub.new_command(NewCommandDefinition(TraceableString("test", None), 0, TraceableString("TEST\\xspace", None)))
        s = apply_substitution_rules(TraceableString("Bla \\test asd \\test{}.", None),
                                     [sub])
        self.assertEqual(str(s), "Bla TEST\\xspace asd TEST\\xspace{}.")

    def test3(self):
        sub = NewCommandSubstitution()
        sub.new_command(NewCommandDefinition(TraceableString("test", None), 0, TraceableString("TEST", None)))
        s = apply_substitution_rules(TraceableString("Bla \\test asd \\test{}.", None),
                                     [sub])
        self.assertEqual(str(s), "Bla TEST{}asd TEST{}.")