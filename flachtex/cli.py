from .comments import remove_comments
from .parser import expand_file
import json
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='flachtex: Traceable LaTeX flattening.')
    parser.add_argument('--to_json', action="store_true", help='Return a json.')
    parser.add_argument('--remove_comments', action="store_true", help="Remove comments.")
    parser.add_argument('path', nargs=1, help="Path to main.tex")
    args = parser.parse_args()
    doc = expand_file(args.path[0])
    if args.remove_comments:
        doc = remove_comments(doc)
    if args.to_json:
        print(json.dumps(doc.to_json()))
    else:
        print(str(doc))
