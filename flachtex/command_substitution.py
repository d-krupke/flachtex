"""
LaTeX allows you to define your own commands using `\newcommand`.
This can be a useful feature for many scenarios, but it complicates the source.
Thus, this file implements some logic to substitute these usages by their definition.
"""

import re
import typing

from flachtex.traceable_string import TraceableString
from flachtex.command_finder import CommandFinder
from flachtex.rules import SubstitutionRule, Substitution


class NewCommandDefinition:
    """
    For defining a LaTeX-command definition with `\\newcommand`. Note that optional
    parameters are not supported right now.
    """

    def __init__(
        self, name: TraceableString, num_parameters: int, command: TraceableString
    ):
        """
        :param name: The name of the command.
        :param num_parameters: The number of (mandatory parameters).
        :param command: The actual command definition.
        """
        self.name = name
        self.num_parameters = num_parameters
        self.command = command

    def __repr__(self):
        return f"\\newcommand{{{self.name}}}[{self.num_parameters}]{{{self.command}}}"


def find_new_commands(
    latex_document: TraceableString,
) -> typing.Iterable[NewCommandDefinition]:
    """
    Find all commands defined by `\newcommand`. Not compatible with optional commands
    right now.
    :param latex_document: The LaTeX-document to be scanned.
    :return: Iterator on all command definitions.
    """
    cf = CommandFinder(strict=True)
    cf.add_command("newcommand", 2, 1)
    for match in cf.find_all(str(latex_document)):
        command_name = latex_document[match.parameters[0][0] : match.parameters[0][1]]
        command = latex_document[match.parameters[1][0] : match.parameters[1][1]]
        if match.opt_parameters[0]:
            opt_par_range = match.opt_parameters[0]
            num_parameters = int(
                str(latex_document[opt_par_range[0] : opt_par_range[1]])
            )
        else:
            num_parameters = 0
        yield NewCommandDefinition(command_name, num_parameters, command)


class NewCommandSubstitution(SubstitutionRule):
    """
    Substitute commands defined, e.g., by \newcommand.
    Currently, default parameters are not supported.
    """

    def __init__(self):
        self._commands = {}
        self._command_finder = CommandFinder()

    def new_command(self, definition: NewCommandDefinition) -> None:
        """
        Add a new command definition that will be replaced.
        :param definition: The definition of the command
        :return: None
        """
        name = str(definition.name).strip()
        if name[0] == "\\":
            name = name[1:]
        if name in self._commands:
            print(
                f"%WARNING: Multiple definitions of command '{name}'."
                f" Substitution may be buggy."
            )
        self._commands[name] = definition
        print("%LOG: Detected", definition)
        self._command_finder.add_command(name, definition.num_parameters)

    def _get_substitution(
        self, command: TraceableString, parameters: typing.List[TraceableString]
    ) -> TraceableString:
        for i, p in enumerate(parameters):
            offset = 0
            for match in re.findall(f"#{i}([^0-9]|$)", str(command), re.MULTILINE):
                command = (
                    command[: match.start() + offset]
                    + p
                    + command[match.end() + offset :]
                )
                offset += len(p) - (match.end() - match.start())
        return command

    def find_all(self, content: TraceableString) -> typing.Iterable[Substitution]:
        for match in self._command_finder.find_all(str(content)):
            definition = self._commands[str(match.command)]
            parameters = [content[p[0] : p[1]] for p in match.parameters]
            sub = self._get_substitution(definition.command, parameters)
            yield Substitution(match.start, match.end, sub)
