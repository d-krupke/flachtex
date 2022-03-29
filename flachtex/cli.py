from .comments import remove_comments
from .parser import expand_file, expand_file_and_attach_sources
import json
import argparse


def main():
    parser = argparse.ArgumentParser(description='flachtex: Traceable LaTeX flattening.')
    parser.add_argument('--to_json', action="store_true", help='Return a json.')
    parser.add_argument('--remove_comments', action="store_true", help="Remove comments.")
    parser.add_argument('--attach', action='store_true', help="Attach sources to json.")
    parser.add_argument('path', nargs=1, help="Path to main.tex")
    args = parser.parse_args()
    if not args.path:
        parser.print_help()
        exit(1)
    if args.attach:
        doc, sources = expand_file_and_attach_sources(args.path[0])
    else:
        doc = expand_file(args.path[0])
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
