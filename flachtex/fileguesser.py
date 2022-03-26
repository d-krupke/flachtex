import typing
import os

from flachtex.filereader import FileReader


class FileGuesser:
    """
    Tries different combinations to find a file. Sometimes a tex file is imported without a "tex" at the end or it
    is located in a parent folder or at the root. This code tries to find the best match without too much fuss.
    """

    def __init__(self, file_reader=None):
        if not file_reader:
            file_reader = FileReader()
        self.file_reader = file_reader

    def get_file_content(self, path: str, origin: typing.Optional[str] = None):
        if not origin:
            origin = ""
        for path in self._iterate_options_with_origin(path, origin):
            try:
                content =  str(self.file_reader[path])
                return path, content
            except KeyError as ke:
                pass
        raise KeyError("Could not find file for {path} and origin {origin}")

    def _iterate_options_with_origin(self, path: str, origin: str):
        while origin:
            yield os.path.join(origin, path)
            yield os.path.join(origin, path) + ".tex"
            origin = os.path.dirname(origin)
        yield path
        yield path + ".tex"
