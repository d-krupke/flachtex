"""
In this file, the rules for including other documents are defined.
You can easily add your own rules using the decorator.
Best do it in this file to ensure that it is actually executed.
"""
import abc
import re
import typing

import os


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


class SkipRule(abc.ABC):

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
            r"(?P<skipped_part>(^\s*%%FLACHTEX-SKIP-START).*?(^\s*%%FLACHTEX-SKIP-STOP))")

    def determine_skip(self, match: re.Match):
        span_to_be_skipped = Range(match.start("skipped_part"), match.end("skipped_part"))
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
        import_path = os.path.join(match.group("dir").strip(), match.group("file").strip())
        return Import(match.start("command"), match.end("command"), import_path)


# %%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]
class ExplicitImportRule(RegexIncludeRule):
    def __init__(self):
        super().__init__(
            r"^\s*(?P<command>%%FLACHTEX-EXPLICIT-IMPORT\[(?P<path>[^}]*)\])")

    def determine_include(self, match: re.Match):
        # We are using the group feature of regex to extract the path (<path>)
        # as well as the part to be replaced (<command>)
        import_path = match.group("path").strip()
        return Import(match.start("command"), match.end("command"), import_path)


BASIC_INCLUDE_RULES = [NativeIncludeRule(), SubimportRule(), ExplicitImportRule()]
BASIC_SKIP_RULES = [BasicSkipRule()]
