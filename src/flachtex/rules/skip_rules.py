"""
Some parts should be skipped for the flattening. Here you can specify corresponding
rules.
"""

import abc
import re
import typing

from ..command_finder import CommandFinder
from ..traceable_string import TraceableString
from ..utils import Range


class SkipRule(abc.ABC):
    """
    A rule that defines, which parts should be skipped.
    """

    @abc.abstractmethod
    def find_all(self, content) -> typing.Iterable[Range]:
        pass


class RegexSkipRule(SkipRule):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    def find_all(self, content) -> typing.Iterable[Range]:
        for match in self.regex.finditer(content):
            yield self.determine_skip(match)

    @abc.abstractmethod
    def determine_skip(self, match: re.Match) -> Range:
        pass


class TodonotesRule(SkipRule):
    """
    Skips all the comments added with \\usepackage{todonotes}, or more concrete, all
    commands with \\todo[...]{...}.
    """

    def find_all(self, content) -> typing.Iterable[Range]:
        cf = CommandFinder()
        cf.add_command("todo", 1, 1)
        for match in cf.find_all(str(content)):
            yield Range(match.start, match.end)


class BasicSkipRule(RegexSkipRule):
    """
        Skips parts of the form
        ```
    %%FLACHTEX-SKIP-START
    ...
    %%FLACHTEX-SKIP-STOP
    """

    def __init__(self):
        super().__init__(
            r"(?P<skipped_part>(^\s*%%FLACHTEX-SKIP-START).*?(^\s*%%FLACHTEX-SKIP-STOP))"
        )

    def determine_skip(self, match: re.Match):
        return Range(match.start("skipped_part"), match.end("skipped_part"))


class CommentsPackageSkipRule(RegexSkipRule):
    """
    Skips all the comments added with the `comment` package, or more concrete, all
    content between `\\begin{comment}` and `\\end{comment}`.
    """

    def __init__(self):
        # Match \begin{comment} ... \end{comment}, including all lines between, and trailing newline
        super().__init__(
            r"(?P<skipped_part>[ \t]*\\begin{comment}\s*.*?\\end{comment}[ \t]*\n?)"
        )

    def determine_skip(self, match: re.Match):
        return Range(match.start("skipped_part"), match.end("skipped_part"))


def _find_skips(
    content: TraceableString, skip_rules: typing.Iterable[SkipRule]
) -> list[Range]:
    """Find all ranges to skip based on skip rules."""
    content_str = str(content)
    skips: list[Range] = []
    for rule in skip_rules:
        skips += list(rule.find_all(content_str))
    return skips


def _sort_and_check_ranges(skips: list[Range]) -> list[Range]:
    skips.sort()
    for i, e in enumerate(skips[:-1]):
        if e.intersects(skips[i + 1]):
            msg = "Intersecting skipped parts."
            raise ValueError(msg)
    return skips


def apply_skip_rules(
    content: TraceableString, skip_rules: typing.Iterable[SkipRule]
) -> TraceableString:
    """
    Apply a list of SkipRules to a content and return the content removed of all
    parts specified by the rules.
    :param content: The content to be filtered
    :param skip_rules: The rules to be applied
    :return:
    """
    skips = _find_skips(content, skip_rules)
    sorted_skips = _sort_and_check_ranges(skips)
    offset = 0
    for skip in sorted_skips:
        a = content[: skip.start + offset]
        b = content[skip.end + offset :]
        content = a + b
        offset -= len(skip)
    return content
