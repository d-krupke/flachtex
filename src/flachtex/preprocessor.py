import typing

from .cycle_prevention import CyclePrevention
from .filefinder import FileFinder
from .rules import (
    BASIC_INCLUDE_RULES,
    BASIC_SKIP_RULES,
    Import,
    apply_skip_rules,
    apply_subimport_substitution_rules,
    apply_substitution_rules,
    find_imports,
)
from .traceable_string import TraceableString


class Preprocessor:
    def __init__(self, project_root: str):
        """
        :param project_root: The root of the LaTeX-document. Important for resolving
        the relative paths of include statements.
        """
        self.skip_rules = list(BASIC_SKIP_RULES)
        self.subimport_rules = []
        self.substitution_rules = []
        self.import_rules = list(BASIC_INCLUDE_RULES)
        self.file_finder = FileFinder(project_root)
        self.structure = {}

    def read_file(self, file_path: str) -> TraceableString:
        """
        Read a file and apply the SkipRules and SubstitutionRules.
        :param file_path: Path to the file.
        :return: Preprocessed file content
        """
        content = TraceableString(self.file_finder.read(file_path), origin=file_path)
        content = apply_skip_rules(content, self.skip_rules)
        content = apply_substitution_rules(content, self.substitution_rules)
        return content

    def include_path(
        self, content: TraceableString, subimport_path: str
    ) -> TraceableString:
        if subimport_path is None or subimport_path == "":
            return content
        content = apply_subimport_substitution_rules(
            content, self.subimport_rules, subimport_path
        )
        return content

    def find_imports(self, content: TraceableString) -> typing.List[Import]:
        """
        Find all imports within the file content (based on the import rules).
        :param content: The content of the LaTeX-file.
        :return: List of imports in the content.
        """
        imports = find_imports(content, self.import_rules)
        return imports

    def _add_structure(self, path: str, included_files: typing.List[str]):
        self.structure[path] = {
            "content": self.file_finder.read(path),
            "includes": included_files,
        }

    def expand_file(
        self,
        file_path: str,
        _cycle_prevention: typing.Optional[CyclePrevention] = None,
        is_subimport: bool = False,
        subimport_path: str = None,
    ) -> TraceableString:
        """
        Expand/flatten the file. This is performed recursively, but there will be an
        excepetion in case of cyclic include-commands.
        :param file_path: The path to the file to be included.
        :param _cycle_prevention: Internal use for preventing cyclic inclusions.
        :return: A flat LaTeX-document containing all included files.
        """
        _cycle_prevention = (
            _cycle_prevention if _cycle_prevention else CyclePrevention()
        )
        offset = 0
        _cycle_prevention.push(file_path, context=file_path)
        content = self.read_file(file_path)
        imports = self.find_imports(content)
        self._add_structure(file_path, [import_.path for import_ in imports])
        for match in imports:
            insertion_file = self.file_finder.find_best_matching_path(
                match.path, origin=file_path
            )
            insertion = self.expand_file(
                insertion_file,
                _cycle_prevention,
                match.is_subimport,
                match.subimport_path,
            )
            content = (
                content[: match.start + offset]
                + insertion
                + content[match.end + offset :]
            )
            offset += len(insertion) - len(match)
        if is_subimport:
            content = self.include_path(content, subimport_path)
        _cycle_prevention.pop()
        return content
