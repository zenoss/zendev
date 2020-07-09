

def restore(args, env):
    env().restore(args.name, shallow=args.shallow)


def add_commands(subparsers, completer):
    restore_parser = subparsers.add_parser(
        "restore", help="Restore repository state to a tag"
    )
    restore_parser.add_argument(
        "--shallow", action="store_true", help="Attempt a shallow clone"
    )
    a = restore_parser.add_argument("name", metavar="NAME")
    a.completer = completer
    restore_parser.set_defaults(functor=restore)

    # TODO: add support for tag and changelog ala zendev v1
