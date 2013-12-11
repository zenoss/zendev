import sys

from .utils import colored

def info(msg):
    print >> sys.stderr, colored('==>', 'blue'), colored(msg, 'white')

def error(msg):
    print >> sys.stderr, colored('==>', 'red'), colored(msg, 'white')

def ask(msg, response):
    print >> sys.stderr, colored('==>', 'green'), colored(msg, 'white')
    print >> sys.stderr, colored('==>', 'green'), colored(response, 'white')
    return raw_input()
