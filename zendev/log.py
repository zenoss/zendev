from __future__ import print_function

import sys

from .utils import colored


def info(msg):
    if sys.stdout.isatty():
        print(
            colored("ZENDEV:", "magenta"), colored(msg, "magenta"),
            file=sys.stderr,
        )
    else:
        print(msg, file=sys.stderr)


def error(msg):
    if sys.stdout.isatty():
        print(colored("ZENDEV:", "red"), colored(msg, "red"), file=sys.stderr)
    else:
        print(msg, file=sys.stderr)


def ask(msg, response):
    print(colored("ZENDEV:", "green"), colored(msg, "white"), file=sys.stderr)
    print(
        colored("ZENDEV:", "green"), colored(response, "white"),
        file=sys.stderr,
    )
    return raw_input()
