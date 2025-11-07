import abc
import re
import typing
from pathlib import Path

from flachtex.command_finder import CommandFinder
from flachtex.traceable_string import TraceableString
from flachtex.utils import Range


class Import(Range):
    def __init__(
        self,
        start: int,
        end: int,
        path: str,
        is_subimport: bool,
        subimport_path: str | None,
    ):
        super().__init__(start, end)
        self.path = path
        self.is_subimport = is_subimport if not None else False
        self.subimport_path = subimport_path


class ImportRule(abc.ABC):
    @abc.abstractmethod
    def find_all(self, content: str) -> typing.Iterable[Import]:
        pass


class RegexImportRule(ImportRule):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    @abc.abstractmethod
    def determine_include(self, match: re.Match) -> Import:
        pass

    def find_all(self, content: str) -> typing.Iterable[Import]:
        for match in self.regex.finditer(content):
            yield self.determine_include(match)


class NativeImportRule(ImportRule):
    """
    Detects includes of the form `\\input{/path/file.tex}` and `\\include{/path/file.tex}`

    Uses CommandFinder instead of regex to properly handle multiple commands on the same line
    and correctly handle comments and escaping.
    """

    def __init__(self):
        self.finder = CommandFinder()
        self.finder.add_command("input", num_params=1)
        self.finder.add_command("include", num_params=1)

    def find_all(self, content: str) -> typing.Iterable[Import]:
        for match in self.finder.find_all(content):
            if match.parameters:
                path_start, path_end = match.parameters[0]
                import_path = content[path_start:path_end].strip()
                yield Import(match.start, match.end, import_path, False, None)


class SubimportRule(RegexImportRule):
    """
    Detects imports by the subimport package.
    These can have the form `\\subimport{path}{file}` or  `\\subimport*{path}{file}`.
    """

    expr = r"^(([^%])|(\\%))*?(?P<command>\\subimport\*?\{(?P<dir>[^}]*)\}\{(?P<file>[^}]*)\})"

    def __init__(self):
        super().__init__(self.expr)

    def determine_include(self, match: re.Match):
        # This function implements the functionality for the subimports library.
        # The import is separated into two parts
        subimport_path = match.group("dir").strip()
        import_path = str(
            Path(match.group("dir").strip()) / match.group("file").strip()
        )
        return Import(
            match.start("command"),
            match.end("command"),
            import_path,
            True,
            subimport_path,
        )


# %%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]
class ExplicitImportRule(RegexImportRule):
    def __init__(self):
        super().__init__(
            r"^\s*(?P<command>%%FLACHTEX-EXPLICIT-IMPORT\[(?P<path>[^}]*)\])"
        )

    def determine_include(self, match: re.Match):
        # We are using the group feature of regex to extract the path (<path>)
        # as well as the part to be replaced (<command>)
        import_path = match.group("path").strip()
        return Import(
            match.start("command"), match.end("command"), import_path, False, None
        )


def _sort_imports(imports: list[Import]) -> list[Import]:
    imports.sort()
    for i, e in enumerate(imports[:-1]):
        if e.intersects(imports[i + 1]):
            msg = "Intersecting imports."
            raise ValueError(msg)
    return imports


def find_imports(
    content: TraceableString, include_rules: typing.Iterable[ImportRule]
) -> list[Import]:
    content_ = str(content)
    imports = []
    for rule in include_rules:
        imports += list(rule.find_all(content_))
    return _sort_imports(imports)
