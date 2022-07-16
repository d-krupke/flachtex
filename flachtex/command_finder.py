"""
Parsing LaTeX-commands perfectly is difficult, because the rules are quite complex.
There are many attempts using regular expressions, but I haven't seen one that
could not be tricked.
The following code can still be tricked by implicit parameters (no brackets {}),
but otherwise should be safe.
"""

import typing


class LatexStream:
    """
    The LatexStreams job is to keep track of the reading position and
    whether we are currently in a comment section or the current symbol
    is escaped.
    """

    def __init__(self, text, pos=0):
        self._text = text
        self._pos = pos
        self.is_escaped = False
        self.in_comment = False
        self._read_escape = False

    def next(self) -> str:
        """
        Return the next character and move the cursor the next position.
        Update the current status regarding comment or escaping.
        :return: Next character.
        """
        c = self._text[self._pos]
        self._pos += 1
        if self._read_escape:
            self._read_escape = False
            self.is_escaped = True
        else:
            self.is_escaped = False
        if not self.is_escaped and c == "%":
            self.in_comment = True
        if c == "\n":
            self.in_comment = False
        if not self.in_comment and not self.is_escaped and c == "\\":
            assert self._read_escape == False
            self._read_escape = True
        else:
            self._read_escape = False
        return c

    def peek(self, pure=False) -> typing.Optional[str]:
        """
        Return the current character. Do not move the cursor.
        :param pure: Only return characters that are not in a comment or escaped.
        :return: Next character.
        """
        if pure and (self._read_escape or self.in_comment):
            return None
        c = self._text[self._pos]
        return c

    def has_next(self) -> bool:
        """
        Returns whether there is a next character.
        :return: True if there is a next character.
        """
        return self._pos < len(self._text)

    def pos(self) -> int:
        """
        Current position of the cursor.
        :return: Position of the cursor.
        """
        return self._pos

    def skip_whitespace_and_comments(self) -> None:
        """
        Skips over all whitespace characters and comments.
        :return: None
        """
        while self.in_comment or (self.peek().isspace() and not self.is_escaped):
            self.next()

    def __iter__(self):
        """
        Iterate over all characters. You can use the other methods during the
        iteration, allowing you for example to skip all whitespaces and comments
        in the loop.
        :return: All characters.
        """
        while self.has_next():
            c = self.next()
            yield c


class CommandMatch:
    """
    A match of the CommandFinder.
    """

    def __init__(
        self,
        command: str,
        start: int,
        end: int,
        parameters: typing.List[typing.Tuple[int, int]],
        opt_parameters: typing.List[typing.Optional[typing.Tuple[int, int]]],
    ):
        self.command = command  # command name
        self.start = start  # position of the start of the command
        self.end = end  # position after the last parameter of the command
        self.parameters = parameters  # list of the mandatory parameters
        self.opt_parameters = opt_parameters  # list of the optional parameters

    def __repr__(self):
        return (
            f"{self.start}:{self.end} \\{self.command}"
            + "["
            + "".join(f"{p[0]}:{p[1]}" if p else "None" for p in self.opt_parameters)
            + "]"
            + "".join("{" + str(p[0]) + ":" + str(p[1]) + "}" for p in self.parameters)
        )

    def __eq__(self, other):
        return (
            self.command,
            self.start,
            self.end,
            self.parameters,
            self.opt_parameters,
        ) == (
            other.command,
            other.start,
            other.end,
            other.parameters,
            other.opt_parameters,
        )


class CommandFinder:
    """
    Finds occurrences of latex commands in a string and provides you with
    the position and nicely parsed parameters.
    """

    def __init__(self, strict=False):
        self._strict = strict
        self._commands = {}

    def add_command(self, name, num_params=1, num_opt=0):
        """
        :param name:
        :param num_params:
        :param num_opt:
        :return:
        """
        self._commands[name] = (num_params, num_opt)
        return self

    def _read_parameters(self, stream, name: str):
        if name not in self._commands:
            return [], []
        n, n_opt = self._commands[name]
        opt_params = [
            self._read_parameter(stream, "[", "]", False) for _ in range(n_opt)
        ]
        params = [self._read_parameter(stream, "{", "}") for _ in range(n)]
        return opt_params, params

    def _read_command_name(self, stream):
        stream.skip_whitespace_and_comments()
        if not stream.peek(True) == "\\":
            raise ValueError(f"No command. Next character is '{stream.peek()}'.")
        command = ""
        stream.next()  # skip '\'
        while stream.peek().isalpha():
            command += stream.next()
        return command

    def _read_parameter(
        self, stream: LatexStream, begin: str, end: str, mandatory=True
    ):
        stream.skip_whitespace_and_comments()
        if not mandatory and stream.peek(True) != begin:
            # No begin-symbol ({[) -> no parameter if not mandatory
            return None
        if stream.peek(True) == begin:  # properly encapsulated parameter.
            depth = 1
            stream.next()
            start = stream.pos()  # after {[
            while depth > 0:
                if stream.peek(True) == begin:
                    depth += 1
                if stream.peek(True) == end:
                    depth -= 1
                stream.next()
            return (start, stream.pos() - 1)  # at }]
        else:  # parameter without begin/end-symbols ([],{})
            if self._strict:
                print(stream._text[stream.pos() - 10 : stream.pos() + 10])
                raise ValueError("Parameters without brackets.")
            start = stream.pos()
            if stream.peek() == "\\":
                print("WARNING: Ambiguous parameters due to missing brackets.")
                command_name = self._read_command_name(stream)
                self._read_parameters(stream, command_name)
                return (start, stream.pos())
            else:
                stream.next()
                return (start, stream.pos())

    def _read_new_command_parameters(self, stream: LatexStream):
        command_name = self._read_parameter(stream, "{", "}", mandatory=True)
        opt_params = [self._read_parameter(stream, "[", "]", mandatory=False)]
        definition = self._read_parameter(stream, "{", "}", mandatory=True)
        return opt_params, [command_name, definition]

    def find(self, text: str, begin: int = 0) -> typing.Optional[CommandMatch]:
        """
        Find first occurrence of a command in the text.
        :param text: The text to be searched.
        :param begin: The point to start in the text.
        :return:
        """
        stream = LatexStream(text, begin)
        while stream.has_next():
            if stream.peek(True) == "\\":
                begin = stream.pos()
                command = self._read_command_name(stream)
                if command in ("newcommand", "renewcommand"):
                    if command in self._commands:
                        opt_params, params = self._read_new_command_parameters(stream)
                        end = stream.pos()
                        return CommandMatch(command, begin, end, params, opt_params)
                    else:
                        #  In the \\newcommand definition, the commands are not actually
                        # applied, so we want to skip them.
                        self._read_parameter(stream, "{", "}")  # skip definition name
                elif command in self._commands:
                    opt_params, params = self._read_parameters(stream, command)
                    end = stream.pos()
                    return CommandMatch(command, begin, end, params, opt_params)
            else:
                stream.next()
        return None

    def find_all(self, text: str):
        begin = 0
        result = self.find(text, begin)
        while result:
            yield result
            begin = result.end
            result = self.find(text, begin)
