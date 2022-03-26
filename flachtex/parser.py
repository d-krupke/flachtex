import typing

from flachtex.fileguesser import FileGuesser
from flachtex.filereader import FileReader
from flachtex.flattened_document import FlattenedDocument
from flachtex.originawarestr import OriginAwareString
from flachtex.rules import IncludeRule, SkipRule


class CycleException(Exception):
    def __init__(self, path, origin):
        self.path = path
        self.origin = origin

    def __str__(self):
        return f"CycleException importing {self.path} from {self.origin}"


class Flattener:
    def __init__(self,
                 file_guesser: typing.Optional[FileGuesser] = None,
                 include_rules: typing.Optional[typing.List[IncludeRule]] = None,
                 skip_rules: typing.Optional[typing.List[SkipRule]] = None):
        self.skip_rules = skip_rules if skip_rules else []
        self.include_rules = include_rules if include_rules else []
        self.file_guesser = file_guesser if file_guesser else FileGuesser(FileReader())

    def flatten(self, root: str):
        path, content = self.file_guesser.get_file_content(root)
        files_read = {path}
        content = OriginAwareString(content, path)
        changes = True
        while changes:
            content = self._apply_skip_rules(content)
            content, changes = self._apply_first_import_rule(content,
                                                             files_read)
        return FlattenedDocument(content, self.file_guesser)

    def _apply_skip_rules(self, content):
        for rule in self.skip_rules:
            match = rule.regex.search(str(content))
            while match:
                span = rule.determine_skip(match)
                content = content[:span[0]] + content[span[1]:]
                match = rule.regex.match(str(content))
        return content

    def _apply_first_import_rule(self, content, files_read):
        for rule in self.include_rules:
            match = rule.regex.search(str(content))
            if match:
                span, include_path = rule.determine_include(match)
                origin = content.get_origin(span[0])
                normalized_path, insertion = self.file_guesser.get_file_content(
                    include_path,
                    origin[1])
                print("in", origin, "replace", content[span[0]:span[1]], "by content of",
                      normalized_path)
                if normalized_path in files_read:
                    raise CycleException(include_path, origin)
                content = content[:span[0]] \
                          + OriginAwareString(insertion, normalized_path) \
                          + content[span[1]:]
                return content, True
        return content, False
