"""
Removing comments can only be done at the end as comments can be used for
directives for flachtex. Removing them already in the preprocessor would potentially
lead to unwanted effects.
If you don't want comments, simply apply the function below to the output.
"""
import re

from .traceable_string import TraceableString


def remove_comments(content: TraceableString) -> TraceableString:
    """
    Remove the comments out of the content.
    :param content:
    :return:
    """
    regex = re.compile(r"^.*?(?<!\\)(?P<comment>%..*\n)", re.MULTILINE)
    comments = []
    for match in regex.finditer(str(content)):
        comments.append((match.start("comment"), match.end("comment")))
    comments.sort()
    offset = 0
    for comment in comments:
        content = content[: comment[0] + offset] + content[comment[1] + offset :]
        offset -= comment[1] - comment[0]
    return content
