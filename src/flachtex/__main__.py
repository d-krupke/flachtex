import argparse
import json
from pathlib import Path

from .command_substitution import NewCommandSubstitution, find_new_commands
from .comments import remove_comments
from .formatter import format_latex
from .preprocessor import Preprocessor
from .rules import ChangesRule, SubimportChangesRule, TodonotesRule


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for flachtex."""
    # Epilog with examples
    epilog = """
examples:
  # Flatten multi-file project for arXiv submission
  flachtex main.tex > arxiv_submission.tex

  # Format for version control (one sentence per line)
  flachtex --format --indent 2 main.tex > formatted.tex

  # Format without flattening (keep \\input commands)
  flachtex --no-expand --format --indent 2 main.tex

  # Clean version for journal (remove comments, TODOs)
  flachtex --comments --todos main.tex > submission.tex

  # Full pipeline: flatten, format, clean
  flachtex --format --indent 2 --comments --todos main.tex > clean.tex

  # Process with newcommand substitution
  flachtex --newcommand main.tex > expanded.tex

protection markers:
  %%FLACHTEX-EXCLUDE-START/STOP     Exclude content from output
  %%FLACHTEX-UNCOMMENT-START/STOP   Activate commented content
  %%FLACHTEX-RAW-START/STOP         Bypass all preprocessing
  %%FLACHTEX-NO-FORMAT-START/STOP   Skip formatting only

more info:
  Documentation: https://github.com/d-krupke/flachtex
  Report issues: https://github.com/d-krupke/flachtex/issues
"""

    parser = argparse.ArgumentParser(
        prog="flachtex",
        description="Flatten and preprocess LaTeX documents with full traceability.\n"
                    "Supports multi-file projects, formatting for version control, "
                    "and various preprocessing options.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional argument
    parser.add_argument(
        "path",
        nargs=1,
        metavar="FILE",
        help="Path to main LaTeX file (e.g., main.tex)",
    )

    # Processing options
    processing = parser.add_argument_group("processing options")
    processing.add_argument(
        "--no-expand",
        action="store_true",
        help="Don't expand \\input and \\include commands (format-only mode)",
    )
    processing.add_argument(
        "--newcommand",
        action="store_true",
        help="Substitute custom commands defined with \\newcommand",
    )
    processing.add_argument(
        "--changes",
        action="store_true",
        help="Process \\usepackage{changes} commands (\\added, \\deleted, etc.)",
    )
    processing.add_argument(
        "--changes_prefix",
        action="store_true",
        help="Use prefix option when processing changes package",
    )

    # Filtering options
    filtering = parser.add_argument_group("filtering options")
    filtering.add_argument(
        "--comments",
        action="store_true",
        help="Remove LaTeX comments from output",
    )
    filtering.add_argument(
        "--todos",
        action="store_true",
        help="Remove \\todo commands from \\usepackage{todonotes}",
    )

    # Formatting options
    formatting = parser.add_argument_group("formatting options")
    formatting.add_argument(
        "--format",
        action="store_true",
        help="Format for version control (one sentence per line, normalized spacing)",
    )
    formatting.add_argument(
        "--indent",
        type=int,
        default=0,
        metavar="N",
        help="Indent nested environments with N spaces (0=disabled, recommended: 2)",
    )

    # Output options
    output = parser.add_argument_group("output options")
    output.add_argument(
        "--to_json",
        action="store_true",
        help="Output as JSON with traceability information",
    )
    output.add_argument(
        "--attach",
        action="store_true",
        help="Attach source files to JSON output (use with --to_json)",
    )

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

    if args.no_expand:
        # Don't expand includes, just read the file directly
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        from .traceable_string import TraceableString

        doc = TraceableString(content, origin=str(file_path))
    else:
        # Normal flattening/expansion
        doc = preprocessor.expand_file(str(file_path))

    # Apply formatting BEFORE comment removal
    # Formatter needs comment markers like %%FLACHTEX-NO-FORMAT-START/STOP
    if args.format:
        doc = format_latex(doc, indent=args.indent, sentence_per_line=True)
    elif args.indent > 0:
        # If indent is specified without --format, apply indentation only (no sentence splitting)
        doc = format_latex(doc, indent=args.indent, sentence_per_line=False)

    # Remove comments at the END, as they may contain directives for flachtex
    if args.comments:
        doc = remove_comments(doc)
        # Normalize blank lines after comment removal
        # (removing comment markers like %%FLACHTEX-RAW-START can leave gaps)
        from flachtex.formatter.normalization import normalize_blank_lines
        doc = normalize_blank_lines(doc)
    if args.to_json:
        data = doc.to_json()
        data["sources"] = preprocessor.structure
        print(json.dumps(data))
    else:
        print(str(doc))


if __name__ == "__main__":
    main()
