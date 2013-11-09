import sys

from .utils import colored

def info(msg):
    print >> sys.stderr, colored('==>', 'blue'), colored(msg, 'white')

def error(msg):
    print >> sys.stderr, colored('==>', 'red'), colored(msg, 'white')

