import sys

from .utils import colored

def info(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('==>', 'blue'), colored(msg, 'grey')
    else:
        print >> sys.stderr, msg

def error(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('==>', 'red'), colored(msg, 'grey')
    else:
        print >> sys.stderr, msg

def ask(msg, response):
    print >> sys.stderr, colored('==>', 'green'), colored(msg, 'grey')
    print >> sys.stderr, colored('==>', 'green'), colored(response, 'grey')
    return raw_input()
