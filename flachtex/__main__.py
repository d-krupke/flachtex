import os
import json
import argparse

from .preprocessor import Preprocessor
from .command_substitution import find_new_commands, NewCommandSubstitution
from .rules import ChangesRule, TodonotesRule
from .comments import remove_comments


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="flachtex: Traceable LaTeX flattening."
    )
    parser.add_argument("--to_json", action="store_true", help="Return a json.")
    parser.add_argument(
        "--comments", action="store_true", help="Remove comments."
    )
    parser.add_argument("--attach", action="store_true", help="Attach sources to json.")
    parser.add_argument(
        "--changes",
        action="store_true",
        help="Replace the commands of the changes package.",
    )
    parser.add_argument(
        "--changes_prefix",
        action="store_true",
        help="Use the prefix option in changes.",
    )
    parser.add_argument("--todos", action="store_true", help="Remove todo-notes.")
    parser.add_argument(
        "--newcommand",
        action="store_true",
        help="Automatically substitute custom commands.",
    )
    parser.add_argument("path", nargs=1, help="Path to main.tex")
    args = parser.parse_args()
    if not args.path:
        parser.print_help()
        exit(1)
    return args


def find_command_definitions(path) -> NewCommandSubstitution:
    """
    Parse the document once independently to extract new commands.
    :param path:
    :return:
    """
    preprocessor = Preprocessor(os.path.dirname(path))
    doc = preprocessor.expand_file(path)
    cmds = find_new_commands(doc)
    ncs = NewCommandSubstitution()
    for cmd in cmds:
        ncs.new_command(cmd)
    return ncs


def main():
    args = parse_arguments()
    file_path = args.path[0]
    preprocessor = Preprocessor(os.path.dirname(file_path))
    if args.todos:
        preprocessor.skip_rules.append(TodonotesRule())
    if args.changes:
        preprocessor.substitution_rules.append(ChangesRule(args.changes_prefix))
    preprocessor.substitution_rules.append(find_command_definitions(file_path))
    doc = preprocessor.expand_file(file_path)

    if args.comments:
        doc = remove_comments(doc)
    if args.to_json:
        data = doc.to_json()
        data["sources"] = preprocessor.structure
        print(json.dumps(data))
    else:
        print(str(doc))


if __name__ == "__main__":
    main()
