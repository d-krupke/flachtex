import re

from flachtex.tracrable_string import TraceableString


def remove_comments(content: TraceableString) -> TraceableString:
    regex = re.compile(r"^.*?(?<!\\)(?P<comment>%..*\n)", re.MULTILINE)
    comments = []
    for match in regex.finditer(str(content)):
        comments.append((match.start("comment"), match.end("comment")))
    comments.sort()
    offset = 0
    for comment in comments:
        content = content[:comment[0] + offset] + content[comment[1] + offset:]
        offset -= comment[1] - comment[0]
    return content
