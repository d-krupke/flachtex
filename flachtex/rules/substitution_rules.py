"""
Some parts of the LaTeX-document may need to be substituted.
The rules defined in this file allow such a handling.
"""
import abc
import typing

from flachtex.command_finder import CommandFinder
from flachtex.traceable_string import TraceableString

from flachtex.utils import Range


class Substitution(Range):
    def __init__(
            self, start: int, end: int, replacement_text: typing.Optional[TraceableString]
    ):
        super().__init__(start, end)
        assert not replacement_text or isinstance(replacement_text, TraceableString)
        self.replacement_text = replacement_text

    def __repr__(self):
        return f"REPLACEMENT[{self.start}:{self.end}]{{{self.replacement_text}}}"


class SubstitutionRule(abc.ABC):
    @abc.abstractmethod
    def find_all(self, content: TraceableString) -> typing.Iterable[Substitution]:
        pass


class ChangesRule(SubstitutionRule):
    """
    The changes-package (\\usepackage{changes}) allows to highlight changes in the
    current revision (especially for writing journal papers). This rule allows
    to remove all its usage and is actually more robust than the original script
    supplied with the package.
    """

    def __init__(self, prefix=False):
        self._added = "chadded" if prefix else "added"
        self._deleted = "chdeleted" if prefix else "deleted"
        self._replaced = "chreplaced" if prefix else "replaced"
        self._highlight = "chhighlight" if prefix else "highlight"
        self._comment = "chcomment" if prefix else "comment"

    def find_all(self, content: TraceableString) -> typing.Iterable[Substitution]:
        assert isinstance(content, TraceableString)
        cf = CommandFinder()
        cf.add_command(self._added, 1, 1)
        cf.add_command(self._deleted, 1, 1)
        cf.add_command(self._replaced, 2, 1)
        cf.add_command(self._highlight, 1, 1)
        cf.add_command(self._comment, 1, 1)
        for match in cf.find_all(str(content)):
            if match.command in (self._added, self._replaced, self._highlight):
                yield Substitution(
                    match.start,
                    match.end,
                    content[match.parameters[0][0]: match.parameters[0][1]],
                )
            elif match.command in (self._deleted, self._comment):
                yield Substitution(match.start, match.end, None)


def _sort_replacements(
        replacements: typing.List[Substitution]
) -> typing.Iterable[Substitution]:
    replacements.sort()
    if len(replacements) <= 1:
        return replacements
    replacements_ = []
    for i, e in enumerate(replacements[:-1]):
        if e.intersects(replacements[i + 1]):
            continue
        else:
            replacements_ += [e]
    return replacements_


def _find_substitutions(
        content: TraceableString, replacement_rules: typing.List[SubstitutionRule]
) -> typing.List[Substitution]:
    replacements = []
    for rule in replacement_rules:
        replacements += [match for match in rule.find_all(content)]
    return replacements


def apply_substitution_rules(
        content: TraceableString,
        replacement_rules: typing.List[SubstitutionRule],
):
    replacements = _find_substitutions(content, replacement_rules)
    max_itererations = 10
    while replacements and max_itererations:
        replacements = _sort_replacements(replacements)
        offset = 0
        for replacement in replacements:
            if replacement.replacement_text:
                content = (
                        content[: replacement.start + offset]
                        + replacement.replacement_text
                        + content[replacement.end + offset:]
                )
                offset -= len(replacement) - len(replacement.replacement_text)
            else:
                content = (
                        content[: replacement.start + offset]
                        + content[replacement.end + offset:]
                )
                offset -= len(replacement)
        max_itererations -= 1
        replacements = _find_substitutions(content, replacement_rules)
    if max_itererations == 0:
        print("%WARNING: Exceeded maximal replacement iterations.")
    return content
