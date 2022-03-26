"""
In this file, the rules for including other documents are defined.
You can easily add your own rules using the decorator.
Best do it in this file to ensure that it is actually executed.
"""

from flachtex.parser import import_rule
import os


@import_rule(r"^\s*(([^%])|(\\%))*(?P<command>((\\input)|(\\import))\{(?P<path>[^}]*)\})")
def latex_import(match):
    # We are using the group feature of regex to extract the path (<path>)
    # as well as the pat to be replaced (<command>)
    span_to_be_replaced = (match.start("command"), match.end("command"))
    import_path = match.group("path")
    return span_to_be_replaced, import_path


@import_rule(r"^\s*(([^%])|(\\%))*(?P<command>\\subimport\*\{(?P<dir>[^}]*)\}\{(?P<file>[^}]*)\})")
def subimport_import(match):
    # This function implements the functionality for the subimports library.
    span_to_be_replaced = (match.start("command"), match.end("command"))
    # The import is separated into two parts
    import_path = os.path.join(match.group("dir"), match.group("file"))
    return span_to_be_replaced, import_path
