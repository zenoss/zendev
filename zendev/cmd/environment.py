import py

from ..environment import ZenDevEnvironment, init_config_dir, NotInitialized
from ..config import get_config


def init(args, _):
    """
    Initialize an environment.
    """
    path = py.path.local().ensure(args.path, dir=True)
    name = args.path  # TODO: Better name-getting
    config = get_config()
    config.add(name, args.path)
    with path.as_cwd():
        try:
            env = ZenDevEnvironment(name=name, path=path)
        except NotInitialized:
            init_config_dir()
            env = ZenDevEnvironment(name=name, path=path)
        env.manifest.save()
        env.initialize()
        env.use()
    if args.tag:
        env.restore(args.tag)
    return env


def clone(args, _):
    env = ZenDevEnvironment(srcroot=args.output, manifest=args.manifest)
    if args.tag:
        env.restore(args.tag, shallow=args.shallow)
    else:
        env.clone(shallow=args.shallow)


def use(args, env):
    """
    Use a zendev environment.
    """
    env(args.name).use()


def drop(args, env):
    """
    Drop a zendev environment.
    """
    get_config().remove(args.name, not args.purge)


def env(args, env):
    """
    Print the current environment
    """
    print get_config().current


def add_commands(subparsers):
    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('path', metavar="PATH")
    init_parser.add_argument('-t', '--tag', metavar="TAG", required=False)
    init_parser.set_defaults(functor=init)

    use_parser = subparsers.add_parser('use')
    use_parser.add_argument('name', metavar='ENVIRONMENT')
    use_parser.set_defaults(functor=use)

    drop_parser = subparsers.add_parser('drop')
    drop_parser.add_argument('name', metavar='ENVIRONMENT')
    drop_parser.add_argument('--purge', action="store_true")
    drop_parser.set_defaults(functor=drop)

    clone_parser = subparsers.add_parser('clone')
    clone_parser.add_argument('-t', '--tag', metavar='TAG',
                              help="Manifest tag to restore")
    clone_parser.add_argument('-m', '--manifest', nargs='+',
                              metavar='MANIFEST', help="Manifest to use")
    clone_parser.add_argument('-s', '--shallow', action='store_true',
                              help="Only check out the most recent commit for each repo")
    clone_parser.add_argument('output', metavar='SRCROOT',
                              help="Target directory into which to clone")
    clone_parser.set_defaults(functor=clone)


    which_parser = subparsers.add_parser('env')
    which_parser.set_defaults(functor=env)

