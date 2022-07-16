from rules import BASIC_SKIP_RULES, ChangesRule, BASIC_INCLUDE_RULES, TodonotesRule

from comments import remove_comments
from parser import expand_file, expand_file_and_attach_sources
import json
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description='flachtex: Traceable LaTeX flattening.')
    parser.add_argument('--to_json', action="store_true", help='Return a json.')
    parser.add_argument('--remove_comments', action="store_true", help="Remove comments.")
    parser.add_argument('--attach', action='store_true', help="Attach sources to json.")
    parser.add_argument('--changes', action='store_true',
                        help="Replace the commands of the changes package.")
    parser.add_argument('--changes_prefix', action='store_true',
                        help="Use the prefix option in changes.")
    parser.add_argument('--remove_todos', action="store_true", help="Remove todo-notes.")
    parser.add_argument('path', nargs=1, help="Path to main.tex")
    args = parser.parse_args()
    if not args.path:
        parser.print_help()
        exit(1)
    return args

def main():
    args = parse_arguments()

    # rules to apply
    skip_rules = BASIC_SKIP_RULES
    if args.remove_todos:
        skip_rules += [TodonotesRule()]
    replacement_rules = [ChangesRule(args.changes_prefix)] if args.changes else []
    include_rules = BASIC_INCLUDE_RULES

    if args.attach:
        doc, sources = expand_file_and_attach_sources(args.path[0],
                                                      skip_rules=skip_rules,
                                                      replacement_rules=replacement_rules,
                                                      include_rules=include_rules)
    else:
        doc = expand_file(args.path[0],
                          skip_rules=skip_rules,
                          replacement_rules=replacement_rules,
                          include_rules=include_rules)
        sources = None

    if args.remove_comments:
        doc = remove_comments(doc)
    if args.to_json:
        data = doc.to_json()
        if sources:
            data["sources"] = sources
        print(json.dumps(data))
    else:
        print(str(doc))


if __name__ == "__main__":
    main()
