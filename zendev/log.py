import sys

from .utils import colored

def info(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('==>', 'blue'), colored(msg, 'white')
    else:
        print >> sys.stderr, msg

def error(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('==>', 'red'), colored(msg, 'white')
    else:
        print >> sys.stderr, msg

def ask(msg, response):
    print >> sys.stderr, colored('==>', 'green'), colored(msg, 'white')
    print >> sys.stderr, colored('==>', 'green'), colored(response, 'white')
    return raw_input()
