from flachtex import TraceableString
from flachtex.command_substitution import (
    NewCommandDefinition,
    NewCommandSubstitution,
    find_new_commands,
)
from flachtex.rules import apply_substitution_rules

doc1 = TraceableString(
    r"""
\newcommand{\MSClength}{MSC-MS\xspace}
\newcommand{\MSCtotEnergy}{MSC-TE\xspace}
\newcommand{\MSClocEnergy}{MSC-BE\xspace}

\newcommand{\MIPone}{MIP-1\xspace}
\newcommand{\MIPtwo}{MIP-2\xspace}
\newcommand*{\MIPthree}{MIP-3\xspace}
\newcommand{\CPone}{CP-1\xspace}
\newcommand{\CPtwo}{CP-2\xspace}

\newcommand{\cone}{cone\xspace}\newcommand{\cupdot}{\mathbin{\mathaccent\cdot\cup}}
\newcommand*{\mincover}{$\Lambda$-cover\xspace}

\MIPone
""",
    "main.tex",
)


def test_empty():
    cmds = list(find_new_commands(TraceableString("", "Main.tex")))
    assert cmds == []


def test_doc1():
    cmds = list(find_new_commands(doc1))
    assert len(cmds) == 11
    sub = NewCommandSubstitution()
    for cmd in cmds:
        sub.new_command(NewCommandDefinition(cmd.name, cmd.num_parameters, cmd.command))
    replacements = list(sub.find_all(doc1))
    assert len(replacements) == 1


def test_substitution_with_zero_parameters():
    sub = NewCommandSubstitution()
    sub.new_command(
        NewCommandDefinition(
            TraceableString("test", None), 0, TraceableString("TEST\\xspace", None)
        )
    )
    s = apply_substitution_rules(
        TraceableString("Bla \\test asd \\test{}.", None), [sub]
    )
    assert str(s) == "Bla TEST\\xspace asd TEST\\xspace{}."


def test_substitution_with_non_space_replacement():
    sub = NewCommandSubstitution()
    sub.new_command(
        NewCommandDefinition(
            TraceableString("test", None), 0, TraceableString("TEST", None)
        )
    )
    s = apply_substitution_rules(
        TraceableString("Bla \\test asd \\test{}.", None), [sub]
    )
    assert str(s) == "Bla TEST asd TEST{}."


def test_complex_commands():
    doc2 = TraceableString(
        r"""
\newcommand{\test}[2]{#2-#1}
\newcommand{\testa}[2]{#2-#1.}
\newcommand{\testb}[2]{#2#1.}
\begin{document}
\test{a}{b}.\\
\testa{a}{b}.\\
\testb{a}{b}.
\testb{aa}{bb}.
\end{document}
""",
        "main.tex",
    )
    cmds = list(find_new_commands(doc2))
    assert len(cmds) == 3
    sub = NewCommandSubstitution()
    for cmd in cmds:
        sub.new_command(NewCommandDefinition(cmd.name, cmd.num_parameters, cmd.command))
    replacements = list(sub.find_all(doc2))
    assert len(replacements) == 4
    s = apply_substitution_rules(doc2, [sub])
    assert (
        str(s).strip()
        == "\\newcommand{\\test}[2]{#2-#1}\n\\newcommand{\\testa}[2]{#2-#1.}\n\\newcommand{\\testb}[2]{#2#1.}\n\\begin{document}\nb-a.\\\\\nb-a..\\\\\nba..\nbbaa..\n\\end{document}".strip()
    )
