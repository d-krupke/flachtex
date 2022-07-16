"""
Some parts should be skipped for the flattening. Here you can specify correponsing
rules.
"""

import typing
import abc
import re

from ..traceable_string import TraceableString
from ..command_finder import CommandFinder
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
        span_to_be_skipped = Range(
            match.start("skipped_part"), match.end("skipped_part")
        )
        return span_to_be_skipped


def _find_skips(content, skip_rules):
    content = str(content)
    skips = []
    for rule in skip_rules:
        skips += [match for match in rule.find_all(content)]
    return skips


def _sort_and_check_ranges(skips) -> typing.Iterable[Range]:
    skips.sort()
    for i, e in enumerate(skips[:-1]):
        if e.intersects(skips[i + 1]):
            raise ValueError(f"Intersecting skipped parts.")
    return skips


def apply_skip_rules(content: TraceableString,
                     skip_rules: typing.Iterable[SkipRule]) -> TraceableString:
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
        content = content[: skip.start + offset] + content[skip.end + offset:]
        offset -= len(skip)
    return content
