"""
In this file, the rules for including other documents are defined.
You can easily add your own rules using the decorator.
Best do it in this file to ensure that it is actually executed.
"""
import abc
import re
import typing

import os

from .traceable_string import TraceableString
from .command_finder import CommandFinder


class Range:
    def __init__(self, begin: int, end: int):
        self.begin = begin
        self.end = end

    def intersects(self, other):
        # one begin lies within the other
        if self.begin <= other.begin < self.end:
            return True
        if other.begin <= self.begin < self.end:
            return True
        return False

    def __le__(self, other):
        return self.begin <= other.begin

    def __lt__(self, other):
        return self.begin < other.begin

    def __len__(self):
        return self.end - self.begin


class Import(Range):
    def __init__(self, begin: int, end: int, path: str):
        super().__init__(begin, end)
        self.path = path


class Replacement(Range):
    def __init__(
        self, begin: int, end: int, replacement_text: typing.Optional[TraceableString]
    ):
        super().__init__(begin, end)
        assert not replacement_text or isinstance(replacement_text, TraceableString)
        self.replacement_text = replacement_text

    def __repr__(self):
        return f"REPLACEMENT[{self.begin}:{self.end}]{{{self.replacement_text}}}"


class ReplacementRule(abc.ABC):
    @abc.abstractmethod
    def find_all(self, content: TraceableString) -> typing.Iterable[Replacement]:
        pass


class ChangesRule(ReplacementRule):
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

    def find_all(self, content: TraceableString) -> typing.Iterable[Replacement]:
        assert isinstance(content, TraceableString)
        cf = CommandFinder()
        cf.add_command(self._added, 1, 1)
        cf.add_command(self._deleted, 1, 1)
        cf.add_command(self._replaced, 2, 1)
        cf.add_command(self._highlight, 1, 1)
        cf.add_command(self._comment, 1, 1)
        for match in cf.find_all(str(content)):
            if match.command in (self._added, self._replaced, self._highlight):
                yield Replacement(
                    match.start,
                    match.end,
                    content[match.parameters[0][0] : match.parameters[0][1]],
                )
            elif match.command in (self._deleted, self._comment):
                yield Replacement(match.start, match.end, None)


class SkipRule(abc.ABC):
    """
    A rule that defines, which parts should be skipped.
    """

    @abc.abstractmethod
    def find_all(self, content) -> typing.Iterable[Range]:
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


class RegexSkipRule(SkipRule):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    def find_all(self, content) -> typing.Iterable[Range]:
        for match in self.regex.finditer(content):
            yield self.determine_skip(match)

    @abc.abstractmethod
    def determine_skip(self, match: re.Match) -> Range:
        pass


class IncludeRule(abc.ABC):
    @abc.abstractmethod
    def find_all(self, content: str) -> typing.Iterable[Import]:
        pass


class RegexIncludeRule(IncludeRule):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    @abc.abstractmethod
    def determine_include(self, match: re.Match) -> Import:
        pass

    def find_all(self, content: str) -> typing.Iterable[Import]:
        for match in self.regex.finditer(content):
            yield self.determine_include(match)


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


class NativeIncludeRule(RegexIncludeRule):
    """
    Detects includes of the form `\input{/path/file.tex}` and `\include{/path/file.tex}`
    """

    def __init__(self):
        expr = r"^(([^%\n])|(\\%))*(?P<command>((\\input)|(\\include))\{(?P<path>[^}]*?)\})"
        super().__init__(expr)

    def determine_include(self, match: re.Match):
        import_path = match.group("path").strip()
        return Import(match.start("command"), match.end("command"), import_path)


class SubimportRule(RegexIncludeRule):
    """
    Detects imports by the subimport package.
    These can have the form `\subimport{path}{file}` or  `\subimport*{path}{file}`.
    """

    expr = r"^(([^%])|(\\%))*?(?P<command>\\subimport\*?\{(?P<dir>[^}]*)\}\{(?P<file>[^}]*)\})"

    def __init__(self):
        super().__init__(self.expr)

    def determine_include(self, match: re.Match):
        # This function implements the functionality for the subimports library.
        # The import is separated into two parts
        import_path = os.path.join(
            match.group("dir").strip(), match.group("file").strip()
        )
        return Import(match.start("command"), match.end("command"), import_path)


# %%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]
class ExplicitImportRule(RegexIncludeRule):
    def __init__(self):
        super().__init__(
            r"^\s*(?P<command>%%FLACHTEX-EXPLICIT-IMPORT\[(?P<path>[^}]*)\])"
        )

    def determine_include(self, match: re.Match):
        # We are using the group feature of regex to extract the path (<path>)
        # as well as the part to be replaced (<command>)
        import_path = match.group("path").strip()
        return Import(match.start("command"), match.end("command"), import_path)


BASIC_INCLUDE_RULES = [NativeIncludeRule(), SubimportRule(), ExplicitImportRule()]
BASIC_SKIP_RULES = [BasicSkipRule()]
