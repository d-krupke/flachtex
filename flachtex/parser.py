import re
import typing

from flachtex.fileguesser import FileGuesser
from flachtex.filereader import FileReader
from flachtex.flattened_document import FlattenedDocument
from flachtex.originawarestr import OriginAwareString

__import_rules = []


def import_rule(regex):
    def decorator(func):
        __import_rules.append((regex, func))

    return decorator


class CycleException(Exception):
    def __init__(self, path, origin):
        self.path = path
        self.origin = origin

    def __str__(self):
        return f"CycleException importing {self.path} from {self.origin}"


def flatten(root, file_guesser: typing.Optional[FileGuesser] = None):
    if not file_guesser:
        file_guesser = FileGuesser(FileReader())
    path, content = file_guesser.get_file_content(root)
    files_read = {path}
    content = OriginAwareString(content, path)
    changes = True
    while changes:
        changes = False
        for regex, replace_func in __import_rules:
            matcher = re.compile(regex, re.MULTILINE)
            match = matcher.match(str(content))
            if match:
                span, include_path = replace_func(match)
                origin = content.get_origin(span[0])
                normalized_path, insertion = file_guesser.get_file_content(include_path, origin[1])
                if normalized_path in files_read:
                    raise CycleException(include_path, origin)
                content = content[:span[0]] + OriginAwareString(insertion, normalized_path) + content[span[1]:]
                changes = True
    return FlattenedDocument(content, file_guesser)
