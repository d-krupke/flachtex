"""
Some parts of the LaTeX-document may need to be substituted.
The rules defined in this file allow such a handling.
"""

import abc
import logging
import typing

from flachtex.command_finder import CommandFinder, CommandMatch
from flachtex.traceable_string import TraceableString
from flachtex.utils import Range


class SubimportSubstitution(Range):
    def __init__(self, start: int, end: int, replacement_text: TraceableString | None):
        super().__init__(start, end)
        assert not replacement_text or isinstance(replacement_text, TraceableString)
        self.replacement_text = replacement_text

    def __repr__(self):
        return f"REPLACEMENT[{self.start}:{self.end}]{{{self.replacement_text}}}"


class SubimportSubstitutionRule(abc.ABC):
    @abc.abstractmethod
    def find_all(
        self, content: TraceableString, subimport_path: str | None = None
    ) -> typing.Iterable[SubimportSubstitution]:
        pass


class SubimportChangesRule(SubimportSubstitutionRule):
    def __init__(self):
        self._includegraphics = ["includegraphics", 0]
        self._bibliography = ["bibliography", 0]

    def which(self, match: CommandMatch) -> int | None:
        members = [
            attr
            for attr in dir(self)
            if not callable(getattr(self, attr)) and not attr.startswith("__")
        ]
        members = members[1:]
        for m in members:
            if match.command == m[1:]:
                return vars(self)[m][1]
        return None

    def find_all(
        self, content: TraceableString, subimport_path: str | None = None
    ) -> typing.Iterable[SubimportSubstitution]:
        assert isinstance(content, TraceableString)

        # If subimport_path is None, we can't perform path adjustments
        if subimport_path is None:
            return

        cf = CommandFinder()
        cf.add_command(self._includegraphics[0], 1, 1)
        cf.add_command(self._bibliography[0], 1, 0)

        for match in cf.find_all(str(content)):
            pos_path = self.which(match)

            # Skip if pos_path is None (command not recognized)
            if pos_path is None:
                continue

            # Extract the path content
            path_content = content.content[
                match.parameters[pos_path][0] : match.parameters[pos_path][1]
            ]

            if path_content[0:1] == "/":
                yield SubimportSubstitution(
                    match.parameters[pos_path][0],
                    match.parameters[pos_path][1],
                    TraceableString(
                        f"./{subimport_path}/{path_content[1:]}",
                        content.origins,
                    ),
                )
            elif path_content[0:2] == "./":
                yield SubimportSubstitution(
                    match.parameters[pos_path][0],
                    match.parameters[pos_path][1],
                    TraceableString(
                        f"./{subimport_path}/{path_content[2:]}",
                        content.origins,
                    ),
                )
            else:
                yield SubimportSubstitution(
                    match.parameters[pos_path][0],
                    match.parameters[pos_path][1],
                    TraceableString(
                        f"./{subimport_path}/{path_content}",
                        content.origins,
                    ),
                )


def _sort_subimport_replacements(
    replacements: list[SubimportSubstitution],
) -> typing.Iterable[SubimportSubstitution]:
    replacements.sort()
    if len(replacements) <= 1:
        return replacements
    replacements_ = []
    for i, e in enumerate(replacements):
        if e.intersects(replacements[(i + 1) % len(replacements)]):
            continue
        replacements_ += [e]
    return replacements_


def _find_subimport_substitutions(
    content: TraceableString,
    replacement_rules: list[SubimportSubstitutionRule],
    subimport_path: str | None,
) -> list[SubimportSubstitution]:
    replacements = []
    for rule in replacement_rules:
        replacements += list(rule.find_all(content, subimport_path))
    return replacements


def apply_subimport_substitution_rules(
    content: TraceableString,
    replacement_rules: list[SubimportSubstitutionRule],
    subimport_path: str | None,
) -> TraceableString:
    replacements = _find_subimport_substitutions(
        content, replacement_rules, subimport_path
    )
    max_itererations = 10
    while replacements and max_itererations:
        replacements = _sort_subimport_replacements(replacements)
        offset = 0
        for replacement in replacements:
            if replacement.replacement_text:
                content = (
                    content[: replacement.start + offset]
                    + replacement.replacement_text
                    + content[replacement.end + offset :]
                )
                offset -= len(replacement) - len(replacement.replacement_text)
            else:
                content = (
                    content[: replacement.start + offset]
                    + content[replacement.end + offset :]
                )
                offset -= len(replacement)
        return content
    if max_itererations == 0:
        logging.getLogger("flachtex").warning(
            "Exceeded maximal subimport_replacement iterations."
        )
    return content
