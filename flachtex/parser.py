import os.path
import typing

from flachtex.cycle_prevention import CyclePrevention
from flachtex.filefinder import FileFinder
from flachtex.traceable_string import TraceableString
from flachtex.rules import IncludeRule, SkipRule, Import, Range, BASIC_SKIP_RULES, \
    BASIC_INCLUDE_RULES


def find_skips(content, skip_rules):
    content = str(content)
    skips = []
    for rule in skip_rules:
        skips += [match for match in rule.find_all(content)]
    return skips


def sort_and_check_ranges(skips,
                          context: str) -> typing.Iterable[Range]:
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
        content = content[:skip.begin] + content[skip.end:]
        offset -= len(skip)
    return content


def find_imports(content,
                 include_rules: typing.Iterable[IncludeRule]) -> typing.List[Import]:
    content = str(content)
    imports = []
    for rule in include_rules:
        imports += [match for match in rule.find_all(content)]
    return imports


def sort_imports(imports,
                 context: str) -> typing.Iterable[Import]:
    imports.sort()
    for i, e in enumerate(imports[:-1]):
        if e.intersects(imports[i + 1]):
            raise ValueError(f"Intersecting matches in {context}.")
    return imports


def parse(file_path: str,
          file_finder: FileFinder,
          skip_rules: typing.List[SkipRule],
          include_rules: typing.List[IncludeRule]) \
        -> typing.Tuple[TraceableString, typing.Iterable[Import]]:
    content = TraceableString(file_finder.read(file_path), origin=file_path)
    content = apply_skip_rules(content, skip_rules, context=file_path)
    imports = find_imports(content, include_rules)
    sorted_imports = sort_imports(imports, context=file_path)
    return content, sorted_imports


def expand_file(file_path: str,
                skip_rules: typing.List[SkipRule] = BASIC_SKIP_RULES,
                include_rules: typing.List[IncludeRule] = BASIC_INCLUDE_RULES,
                file_finder: FileFinder = None,
                cycle_prevention: CyclePrevention = None,
                cb: typing.Callable[[str, str, str], None] = None) -> TraceableString:
    """
    Expands a file recursively by including all imports as well as skipping all parts
    according to the skip rules.
    :param file_path: The path to the file to be expanded, relative to cwd.
    :param skip_rules: A list of skip rules
    :param include_rules: A list of include rules
    :param file_finder: A file finder (optional).
    :param cycle_prevention: A cycle prevention, added automatically.
    :param  cb: Callback with signature  [in_file: str, include_file: str,  command]->None
                that gets called on every file inclusion.
    :return: Expanded content of the string as traceable string
    """
    cycle_prevention = cycle_prevention if cycle_prevention else CyclePrevention()
    file_finder = file_finder if file_finder else FileFinder(os.path.dirname(file_path),
                                                             file_path)
    content, sorted_imports = parse(file_path, file_finder, skip_rules, include_rules)
    offset = 0
    cycle_prevention.push(file_path, context=file_path)
    for match in sorted_imports:
        insertion_file = file_finder.find_best_matching_path(match.path, origin=file_path)
        if cb:
            cb(file_path, insertion_file,
               content[match.begin + offset:match.end + offset])
        insertion = expand_file(insertion_file, skip_rules,
                                include_rules, file_finder, cycle_prevention, cb)
        content = content[:match.begin + offset] + insertion + content[
                                                               match.end + offset:]
        offset += len(insertion) - len(match)
    cycle_prevention.pop()
    return content


def expand_file_and_attach_sources(file_path: str,
                                   skip_rules: typing.List[SkipRule] = BASIC_SKIP_RULES,
                                   include_rules: typing.List[IncludeRule] = BASIC_INCLUDE_RULES,
                                   file_finder: FileFinder = None,
                                   cycle_prevention: CyclePrevention = None) \
        -> typing.Tuple[TraceableString, typing.Dict]:
    """
    Analogous to `expand_file` but will also return a dict with the used sources.
    The sources have the shape {"path": {"content": "...", "includes": ["include1", ...]}}.
    Thus, not only allowing to see the sources but also which file each source will include.
    """
    sources = {}

    file_finder = file_finder if file_finder else FileFinder(os.path.dirname(file_path),
                                                             file_path)
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

    flattened_doc = expand_file(file_path, skip_rules, include_rules, file_finder, cycle_prevention, cb=cb)

    return flattened_doc, sources
