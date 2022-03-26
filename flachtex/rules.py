"""
In this file, the rules for including other documents are defined.
You can easily add your own rules using the decorator.
Best do it in this file to ensure that it is actually executed.
"""
import abc
import re

from flachtex.rule_manager import include_rule, skip_rule
import os


class SkipRule(abc.ABC):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    @abc.abstractmethod
    def determine_skip(self, match: re.Match):
        pass


class IncludeRule(abc.ABC):
    def __init__(self, regex: str):
        self.regex = re.compile(regex, re.MULTILINE | re.DOTALL)

    @abc.abstractmethod
    def determine_include(self, match: re.Match):
        pass


class BasicSkipRule(SkipRule):
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
        span_to_be_skipped = (match.start("skipped_part"), match.end("skipped_part"))
        return span_to_be_skipped


class NativeIncludeRule(IncludeRule):
    """
    Detects includes of the form `\input{/path/file.tex}` and `\include{/path/file.tex}`
    """
    expr = r"^\s*(([^%])|(\\%))*(?P<command>((\\input)|(\\include))\{(?P<path>[^}]*)\})"

    def __init__(self):
        super().__init__(self.expr)

    def determine_include(self, match: re.Match):
        span_to_be_replaced = (match.start("command"), match.end("command"))
        import_path = match.group("path")
        return span_to_be_replaced, import_path


class SubimportRule(IncludeRule):
    """
    Detects imports by the subimport package.
    These can have the form `\subimport{path}{file}` or  `\subimport*{path}{file}`.
    """

    expr = r"^\s*(([^%])|(\\%))*(?P<command>\\subimport\*?\{(?P<dir>[^}]*)\}\{(?P<file>[^}]*)\})"

    def __init__(self):
        super().__init__(self.expr)

    def determine_include(self, match: re.Match):
        # This function implements the functionality for the subimports library.
        span_to_be_replaced = (match.start("command"), match.end("command"))
        # The import is separated into two parts
        import_path = os.path.join(match.group("dir"), match.group("file"))
        return span_to_be_replaced, import_path


# \subimport{path}{file}
# \subimport*{path}{file}
@include_rule(
    r"^\s*(([^%])|(\\%))*(?P<command>\\subimport\*?\{(?P<dir>[^}]*)\}\{(?P<file>[^}]*)\})")
def subimport_import(match):
    # This function implements the functionality for the subimports library.
    span_to_be_replaced = (match.start("command"), match.end("command"))
    # The import is separated into two parts
    import_path = os.path.join(match.group("dir"), match.group("file"))
    return span_to_be_replaced, import_path


# %%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]
class ExplicitImportRule(IncludeRule):
    def __init__(self):
        super().__init__(
            r"^\s*(?P<command>%%FLACHTEX-EXPLICIT-IMPORT\[(?P<path>[^}]*)\])")

    def determine_include(self, match: re.Match):
        # We are using the group feature of regex to extract the path (<path>)
        # as well as the part to be replaced (<command>)
        span_to_be_replaced = (match.start("command"), match.end("command"))
        import_path = match.group("path")
        return span_to_be_replaced, import_path
