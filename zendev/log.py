from termcolor import colored

def info(msg):
    print colored('==>', 'blue'), colored(msg, 'white')

def error(msg):
    print colored('==>', 'red'), colored(msg, 'white')

