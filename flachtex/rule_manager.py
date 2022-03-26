import re

INCLUDE_RULES = []
SKIP_RULES = []


def include_rule(regex):
    def decorator(func):
        INCLUDE_RULES.append((re.compile(regex, re.MULTILINE | re.DOTALL), func))

    return decorator


def skip_rule(regex):
    def decorator(func):
        SKIP_RULES.append((re.compile(regex, re.MULTILINE | re.DOTALL), func))

    return decorator
