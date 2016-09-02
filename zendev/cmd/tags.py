
from ..log import error


def restore(args, env):
    env().restore(args.name)

def add_commands(subparsers, completer):
    restore_parser = subparsers.add_parser('restore', help='Restore repository state to a tag')
    a = restore_parser.add_argument('name', metavar="NAME")
    a.completer = completer
    restore_parser.set_defaults(functor=restore)

    # TODO: add support for tag and changelog ala zendev v1
