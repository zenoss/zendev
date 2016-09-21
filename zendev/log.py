import sys

from .utils import colored

def info(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('ZENDEV:', 'magenta'), colored(msg, 'magenta')
    else:
        print >> sys.stderr, msg

def error(msg):
    if sys.stdout.isatty():
        print >> sys.stderr, colored('ZENDEV:', 'red'), colored(msg, 'red')
    else:
        print >> sys.stderr, msg

def ask(msg, response):
    print >> sys.stderr, colored('ZENDEV:', 'green'), colored(msg, 'white')
    print >> sys.stderr, colored('ZENDEV:', 'green'), colored(response, 'white')
    return raw_input()
