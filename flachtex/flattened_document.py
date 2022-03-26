from flachtex.fileguesser import FileGuesser
from flachtex.originawarestr import OriginAwareString


class FlattenedDocument:
    """
    This object allows to read the flattened document and also to get the origin of the individual characters.
    """
    def __init__(self, content: OriginAwareString, file_guesser: FileGuesser):
        self._content = content
        self._cached_content = str(content).split("\n")
        self._file_guesser = file_guesser

    def get_origin_of_position(self, pos):
        return self._content.get_origin(pos)

    def get_origin(self, line, pos):

        pass

    def __str__(self):
        return str(self._content)

    def read_lines(self):
        return list(self._cached_content)