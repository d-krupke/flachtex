"""flachtex.command_finder
=================================

Robust (but still heuristic) parsing of LaTeX command invocations.

Why not pure regular expressions?
---------------------------------
LaTeX syntax around commands is context sensitive (e.g. nested braces, escaped
characters, comments started by ``%`` until end of line). Pure regular
expressions easily become brittle and either miss valid constructs or produce
false positives. Here we implement a tiny stateful stream parser that tracks:

* Current position in the input
* Whether we are inside a comment (after an unescaped ``%`` until newline)
* Whether the current character was escaped by a preceding backslash

Scope & Limitations
-------------------
The parser focuses on extracting commands together with their mandatory and
optional parameter spans (character index tuples). Implicit parameters (those
not wrapped in ``{}`` or ``[]``) are accepted in non-strict mode but can still
be ambiguous. In ``strict`` mode they raise an error. We do not attempt full
LaTeX macro expansion here.

Returned Spans
--------------
Parameters are represented as ``(start, end)`` tuples where ``start`` is the
index of the first character inside the delimiters and ``end`` is the index of
the last character (inclusive). Optional parameters may be ``None`` if they are
missing.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import NamedTuple

_logger = logging.getLogger(__file__)


class _ParserError(ValueError):
    def __init__(self, msg, position):
        super().__init__(msg)
        self.position = position


ParamSpan = tuple[int, int]
"""Type alias for a (start, end) inclusive character span inside the source text."""

OptParamSpan = ParamSpan | None
"""Optional parameter span; ``None`` means the optional parameter is absent."""


class CommandSpec(NamedTuple):
    """Specification for a LaTeX command.

    Attributes:
        num_params: Number of mandatory ``{}`` delimited parameters.
        num_opt: Number of optional ``[]`` delimited parameters.
    """

    num_params: int
    num_opt: int


class LatexStream:
    """Stateful character stream over LaTeX source.

    Maintains cursor position, comment state and escape state. Provides helper
    methods used by :class:`CommandFinder` while scanning the document.
    """

    def __init__(self, text: str, pos: int = 0):
        self._text = text
        self._pos = pos
        self.is_escaped = False
        self.in_comment = False
        self._read_escape = False

    def next(self) -> str:
        """Consume and return the next character.

        Updates internal state tracking escape sequences and comments.
        Raises:
            _ParserError: If called at end of stream.
        """
        if not self.has_next():
            msg = "No next character."
            raise _ParserError(msg, self._pos)
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
            assert self._read_escape is False
            self._read_escape = True
        else:
            self._read_escape = False
        return c

    def advance(self, n: int = 1) -> None:
        """Advance the cursor ``n`` characters (idempotent at end-of-stream)."""
        for _ in range(n):
            try:
                self.next()
            except _ParserError:
                break

    def peek(self, pure: bool = False) -> str | None:
        """Return current character without consuming it.

        Args:
            pure: If ``True`` return ``None`` when the position is escaped or in
                a comment.
        Returns:
            The current character or ``None``.
        """
        if pure and (self._read_escape or self.in_comment):
            return None
        if not self.has_next():
            return None
        return self._text[self._pos]

    def _peek_is_space(self) -> bool:
        """Return ``True`` if current character is whitespace."""
        peek = self.peek()
        if peek is None:
            return False
        return peek.isspace()

    def has_next(self) -> bool:
        """Return ``True`` if stream has more characters."""
        return self._pos < len(self._text)

    def pos(self) -> int:
        """Return current cursor position (0-based index)."""
        return self._pos

    def skip_whitespace_and_comments(self) -> None:
        """Advance past consecutive whitespace and/or comments."""
        while self.in_comment or (self._peek_is_space() and not self.is_escaped):
            self.next()

    def __iter__(self) -> Iterator[str]:
        """Iterate over remaining characters until end-of-stream."""
        while self.has_next():
            c = self.next()
            yield c


class CommandMatch:
    """Represents a single LaTeX command match.

    Attributes:
        command: Command name without leading backslash (e.g. ``section``).
        start: Index of backslash beginning the command.
        end: Index one past the last character of the final parameter.
        parameters: Mandatory parameter spans.
        opt_parameters: Optional parameter spans or ``None`` if an optional
            parameter was not present.
    """

    def __init__(
        self,
        command: str,
        start: int,
        end: int,
        parameters: list[ParamSpan],
        opt_parameters: list[OptParamSpan],
    ) -> None:
        self.command = command  # command name
        self.start = start  # position of the start of the command
        self.end = end  # position after the last parameter of the command
        self.parameters = parameters  # list of the mandatory parameters
        self.opt_parameters = opt_parameters  # list of the optional parameters

    def __repr__(self) -> str:  # pragma: no cover - repr is for debugging only
        return (
            f"{self.start}:{self.end} \\{self.command}"
            "["
            + "".join(f"{p[0]}:{p[1]}" if p else "None" for p in self.opt_parameters)
            + "]"
            + "".join("{" + str(p[0]) + ":" + str(p[1]) + "}" for p in self.parameters)
        )

    def __eq__(self, other: object) -> bool:  # pragma: no cover - simple structural eq
        if not isinstance(other, CommandMatch):
            return False
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

    def __hash__(self) -> int:  # pragma: no cover - hashing convenience
        return hash(
            (
                self.command,
                self.start,
                self.end,
                tuple(self.parameters),
                tuple(self.opt_parameters),
            )
        )


class CommandFinder:
    """Find LaTeX command invocations within a text.

    Usage pattern:

    >>> cf = CommandFinder().add_command("todo", num_params=1, num_opt=1)
    >>> match = cf.find("Before \\todo[opt]{mandatory} after")
    >>> match.command
    'todo'
    >>> match.parameters  # list of mandatory parameter spans
    [(start_index, end_index)]
    >>> match.opt_parameters  # list of optional parameter spans / None
    [(start_index, end_index)]

    Set ``strict=True`` to reject implicit (non-braced) parameters.
    """

    def __init__(self, strict: bool = False):
        self._strict: bool = strict
        self._commands: dict[str, CommandSpec] = {}

    def add_command(
        self, name: str, num_params: int = 1, num_opt: int = 0
    ) -> CommandFinder:
        """Register a command specification.

        Args:
            name: Command name without leading backslash.
            num_params: Number of mandatory ``{}`` parameters.
            num_opt: Number of optional ``[]`` parameters.
        Returns:
            ``self`` (allows chaining).
        """
        self._commands[name] = CommandSpec(num_params, num_opt)
        return self

    def _read_parameters(
        self, stream: LatexStream, name: str
    ) -> tuple[list[OptParamSpan], list[ParamSpan]]:
        """Read parameters for a previously registered command.

        Returns a tuple ``(optional_params, mandatory_params)`` where optional
        parameters may be ``None`` if omitted.
        """
        if name not in self._commands:
            return [], []
        n, n_opt = self._commands[name]
        opt_params: list[OptParamSpan] = [
            self._read_parameter(stream, "[", "]", False) for _ in range(n_opt)
        ]
        params: list[ParamSpan] = []
        for _ in range(n):
            span = self._read_parameter(stream, "{", "}", True)
            assert span is not None
            params.append(span)
        return opt_params, params

    def _read_command_name(self, stream: LatexStream) -> str:
        stream.skip_whitespace_and_comments()
        if stream.peek(True) != "\\":
            msg = f"No command. Next character is '{stream.peek()}'."
            raise _ParserError(msg, stream.pos())
        command = ""
        stream.next()  # skip '\'
        while stream.has_next():
            nxt = stream.peek()
            if nxt is None or not (nxt.isalpha() or nxt == "*"):
                break
            command += stream.next()
        return command

    def _read_parameter(
        self, stream: LatexStream, begin: str, end: str, mandatory: bool = True
    ) -> OptParamSpan:
        stream.skip_whitespace_and_comments()
        if not mandatory and stream.peek(True) != begin:
            # No begin-symbol ({[) -> no parameter if not mandatory
            return None
        if stream.peek(True) == begin:  # properly encapsulated parameter.
            depth = 1
            stream.advance()
            start = stream.pos()  # after {[
            while depth > 0:
                if stream.peek(True) == begin:
                    depth += 1
                if stream.peek(True) == end:
                    depth -= 1
                stream.advance()
            return (start, stream.pos() - 1)  # at }]
        # parameter without begin/end-symbols ([],{})
        if self._strict:
            context = stream._text[stream.pos() - 10 : stream.pos() + 10]
            msg = f"Parameters without brackets ('{context}')."
            raise _ParserError(msg, stream.pos())
        start = stream.pos()
        if stream.peek() == "\\":
            context = stream._text[stream.pos() - 10 : stream.pos() + 10]
            logging.getLogger("flachtex").warning(
                f"Ambiguous parameters due to missing brackets ('{context}')."
                f" This can lead to corruptions."
            )
            command_name = self._read_command_name(stream)
            self._read_parameters(stream, command_name)
            return (start, stream.pos())
        stream.advance()
        return (start, stream.pos())

    def _read_new_command_parameters(
        self, stream: LatexStream
    ) -> tuple[list[OptParamSpan], list[ParamSpan]]:
        command_name_span = self._read_parameter(stream, "{", "}", mandatory=True)
        assert command_name_span is not None
        opt_params = [self._read_parameter(stream, "[", "]", mandatory=False)]
        definition_span = self._read_parameter(stream, "{", "}", mandatory=True)
        assert definition_span is not None
        return opt_params, [command_name_span, definition_span]

    def find(self, text: str, begin: int = 0) -> CommandMatch | None:
        """Find first registered command occurrence in ``text`` starting at ``begin``.

        Args:
            text: The LaTeX source to search.
            begin: Start index for the scan.
        Returns:
            A :class:`CommandMatch` or ``None`` if no command was found.
        """
        stream = LatexStream(text, begin)
        while stream.has_next():
            try:
                if stream.peek(True) == "\\":
                    begin = stream.pos()
                    command = self._read_command_name(stream)
                    if command in (
                        "newcommand",
                        "renewcommand",
                        "newcommand*",
                        "renewcommand*",
                    ):
                        if command in self._commands:
                            opt_params, params = self._read_new_command_parameters(
                                stream
                            )
                            end = stream.pos()
                            return CommandMatch(command, begin, end, params, opt_params)
                        #  In the \\newcommand definition, the commands are not actually
                        # applied, so we want to skip them.
                        self._read_parameter(stream, "{", "}")  # skip definition name
                    elif command in self._commands:
                        opt_params, params = self._read_parameters(stream, command)
                        end = stream.pos()
                        return CommandMatch(command, begin, end, params, opt_params)

                else:
                    stream.next()
            except _ParserError as pe:
                _logger.error(str(pe))
                stream.advance()
        return None

    def find_all(self, text: str) -> Iterator[CommandMatch]:
        """Yield all command matches (non-overlapping, left-to-right)."""
        begin = 0
        result = self.find(text, begin)
        while result is not None:
            yield result
            begin = result.end
            result = self.find(text, begin)
