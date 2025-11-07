import argparse
import json
from pathlib import Path

from .command_substitution import NewCommandSubstitution, find_new_commands
from .comments import remove_comments
from .preprocessor import Preprocessor
from .rules import ChangesRule, SubimportChangesRule, TodonotesRule


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for flachtex."""
    parser = argparse.ArgumentParser(
        description="flachtex: Traceable LaTeX flattening."
    )
    parser.add_argument("--to_json", action="store_true", help="Return a json.")
    parser.add_argument("--comments", action="store_true", help="Remove comments.")
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


def find_command_definitions(path: Path | str) -> NewCommandSubstitution:
    """
    Parse the document once independently to extract new commands.

    Args:
        path: Path to the LaTeX file

    Returns:
        NewCommandSubstitution with all detected command definitions
    """
    path_obj = Path(path)
    preprocessor = Preprocessor(str(path_obj.parent))
    doc = preprocessor.expand_file(str(path_obj))
    cmds = find_new_commands(doc)
    ncs = NewCommandSubstitution()
    for cmd in cmds:
        ncs.new_command(cmd)
    return ncs


def main() -> None:
    """Main entry point for flachtex command-line interface."""
    args = parse_arguments()
    file_path = Path(args.path[0])
    preprocessor = Preprocessor(str(file_path.parent))
    if args.todos:
        preprocessor.skip_rules.append(TodonotesRule())
    if args.changes:
        preprocessor.substitution_rules.append(ChangesRule(args.changes_prefix))
    if args.newcommand:
        preprocessor.substitution_rules.append(find_command_definitions(file_path))
    preprocessor.subimport_rules.append(SubimportChangesRule())
    doc = preprocessor.expand_file(str(file_path))

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
