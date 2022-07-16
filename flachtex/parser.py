import os.path
import typing

from .cycle_prevention import CyclePrevention
from .filefinder import FileFinder
from .traceable_string import TraceableString
from .rules import (
    IncludeRule,
    SkipRule,
    Import,
    Range,
    BASIC_SKIP_RULES,
    BASIC_INCLUDE_RULES,
    ReplacementRule,
    Replacement,
)


def find_skips(content, skip_rules):
    content = str(content)
    skips = []
    for rule in skip_rules:
        skips += [match for match in rule.find_all(content)]
    return skips


def sort_and_check_ranges(skips, context: str) -> typing.Iterable[Range]:
    skips.sort()
    for i, e in enumerate(skips[:-1]):
        if e.intersects(skips[i + 1]):
            raise ValueError(f"Intersecting matches in {context}.")
    return skips


def apply_skip_rules(content, skip_rules, context):
    skips = find_skips(content, skip_rules)
    sorted_skips = sort_and_check_ranges(skips, context)
    offset = 0
    for skip in sorted_skips:
        content = content[: skip.begin + offset] + content[skip.end + offset :]
        offset -= len(skip)
    return content


def _sort_replacements(
    replacements: typing.List[Replacement], context: str
) -> typing.Iterable[Replacement]:
    replacements.sort()
    if len(replacements) <= 1:
        return replacements
    replacements_ = []
    for i, e in enumerate(replacements[:-1]):
        if e.intersects(replacements[i + 1]):
            continue
        else:
            replacements_ += [e]
    return replacements_


def find_replacements(
    content: TraceableString, replacement_rules: typing.List[ReplacementRule]
) -> typing.List[Replacement]:
    replacements = []
    for rule in replacement_rules:
        replacements += [match for match in rule.find_all(content)]
    return replacements


def apply_replacement_rules(
    content: TraceableString,
    replacement_rules: typing.List[ReplacementRule],
    context: str,
):
    replacements = find_replacements(content, replacement_rules)
    max_itererations = 10
    while replacements and max_itererations:
        replacements = _sort_replacements(replacements, context)
        offset = 0
        for replacement in replacements:
            if replacement.replacement_text:
                content = (
                    content[: replacement.begin + offset]
                    + replacement.replacement_text
                    + content[replacement.end + offset :]
                )
                offset -= len(replacement) - len(replacement.replacement_text)
            else:
                content = (
                    content[: replacement.begin + offset]
                    + content[replacement.end + offset :]
                )
                offset -= len(replacement)
        max_itererations -= 1
        replacements = find_replacements(content, replacement_rules)
    if max_itererations == 0:
        print("%WARNING: Exceeded maximal replacement iterations.")
    return content


def find_imports(
    content: TraceableString, include_rules: typing.Iterable[IncludeRule]
) -> typing.List[Import]:
    content = str(content)
    imports = []
    for rule in include_rules:
        imports += [match for match in rule.find_all(content)]
    return imports


def _sort_imports(
    imports: typing.List[Import], context: str
) -> typing.Iterable[Import]:
    imports.sort()
    for i, e in enumerate(imports[:-1]):
        if e.intersects(imports[i + 1]):
            raise ValueError(f"Intersecting matches in {context}.")
    return imports


def parse(
    file_path: str,
    file_finder: FileFinder,
    skip_rules: typing.List[SkipRule],
    include_rules: typing.List[IncludeRule],
    replacement_rules: typing.List[ReplacementRule],
) -> typing.Tuple[TraceableString, typing.Iterable[Import]]:
    content = TraceableString(file_finder.read(file_path), origin=file_path)
    content = apply_skip_rules(content, skip_rules, context=file_path)
    content = apply_replacement_rules(content, replacement_rules, context=file_path)
    imports = find_imports(content, include_rules)
    sorted_imports = _sort_imports(imports, context=file_path)
    return content, sorted_imports


def expand_file(
    file_path: str,
    skip_rules: typing.List[SkipRule] = BASIC_SKIP_RULES,
    include_rules: typing.List[IncludeRule] = BASIC_INCLUDE_RULES,
    replacement_rules: typing.Optional[typing.List[ReplacementRule]] = None,
    file_finder: typing.Optional[FileFinder] = None,
    cycle_prevention: typing.Optional[CyclePrevention] = None,
    cb: typing.Optional[typing.Callable[[str, str, str], None]] = None,
) -> TraceableString:
    """
    Expands a file recursively by including all imports as well as skipping all parts
    according to the skip rules.
    :param file_path: The path to the file to be expanded, relative to cwd.
    :param skip_rules: A list of skip rules
    :param include_rules: A list of include rules
    :param replacement_rules: A list of replacement rules
    :param file_finder: A file finder (optional).
    :param cycle_prevention: A cycle prevention, added automatically.
    :param  cb: Callback with signature  [in_file: str, include_file: str,  command]->None
                that gets called on every file inclusion.
    :return: Expanded content of the string as traceable string
    """
    cycle_prevention = cycle_prevention if cycle_prevention else CyclePrevention()
    replacement_rules = replacement_rules if replacement_rules else []
    file_finder = (
        file_finder
        if file_finder
        else FileFinder(os.path.dirname(file_path), file_path)
    )
    content, sorted_imports = parse(
        file_path, file_finder, skip_rules, include_rules, replacement_rules
    )
    offset = 0
    cycle_prevention.push(file_path, context=file_path)
    for match in sorted_imports:
        insertion_file = file_finder.find_best_matching_path(
            match.path, origin=file_path
        )
        if cb:
            cb(
                file_path,
                insertion_file,
                content[match.begin + offset : match.end + offset],
            )
        insertion = expand_file(
            insertion_file,
            skip_rules,
            include_rules,
            replacement_rules,
            file_finder,
            cycle_prevention,
            cb,
        )
        content = (
            content[: match.begin + offset] + insertion + content[match.end + offset :]
        )
        offset += len(insertion) - len(match)
    cycle_prevention.pop()
    return content


def expand_file_and_attach_sources(
    file_path: str,
    skip_rules: typing.List[SkipRule] = BASIC_SKIP_RULES,
    include_rules: typing.List[IncludeRule] = BASIC_INCLUDE_RULES,
    replacement_rules: typing.Optional[typing.List[ReplacementRule]] = None,
    file_finder: FileFinder = None,
    cycle_prevention: CyclePrevention = None,
) -> typing.Tuple[TraceableString, typing.Dict]:
    """
    Analogous to `expand_file` but will also return a dict with the used sources.
    The sources have the shape {"path": {"content": "...", "includes": ["include1", ...]}}.
    Thus, not only allowing to see the sources but also which file each source will include.
    """
    sources = {}

    file_finder = (
        file_finder
        if file_finder
        else FileFinder(os.path.dirname(file_path), file_path)
    )

    def make_entry(p):
        if p not in sources:
            source = {}
            source["content"] = file_finder.read(p)
            source["includes"] = []
            sources[p] = source

    make_entry(file_path)

    def cb(file_path, insertion_file, cmd):
        make_entry(insertion_file)
        sources[file_path]["includes"].append(insertion_file)

    flattened_doc = expand_file(
        file_path,
        skip_rules,
        include_rules,
        replacement_rules,
        file_finder,
        cycle_prevention,
        cb=cb,
    )

    return flattened_doc, sources
