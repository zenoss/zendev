import py
import sys

from ..environment import ZenDevEnvironment, init_config_dir, NotInitialized
from ..config import get_config


def init(args, _):
    """
    Initialize an environment.
    """
    path = py.path.local().ensure(args.path, dir=True)
    name = args.path  # TODO: Better name-getting
    config = get_config()

    # Do not allow multiple environment with the same name.
    if config.exists(name):
        print('Zendev environment {} already exists at {}.'.format(
            name, config.environments[name]['path']))
        sys.exit(1)

    config.add(name, args.path)
    with path.as_cwd():
        try:
            env = ZenDevEnvironment(name=name, path=path)
        except NotInitialized:
            init_config_dir()
            env = ZenDevEnvironment(name=name, path=path)
        env.initialize()
        env.use()
    if args.tag:
        env.restore(args.tag)
    return env


def use(args, env):
    """
    Use a zendev environment.
    """
    env(args.name).use(not args.no_switch)


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


def EnvironmentCompleter(prefix, **kwargs):
    return (v for v in get_config().environments.keys() if v.startswith(prefix))


def add_commands(subparsers):
    init_parser = subparsers.add_parser('init', help='Create a new environment')
    init_parser.add_argument('path', metavar="PATH")
    init_parser.add_argument('-t', '--tag', metavar="TAG", required=False)
    init_parser.set_defaults(functor=init)

    use_parser = subparsers.add_parser('use', help='Switch to an environment')
    use_parser.add_argument('name', metavar='ENVIRONMENT').completer = EnvironmentCompleter
    use_parser.add_argument('--no-switch', action="store_true")
    use_parser.set_defaults(functor=use)

    drop_parser = subparsers.add_parser('drop', help='Delete an environment')
    drop_parser.add_argument('name', metavar='ENVIRONMENT').completer = EnvironmentCompleter
    drop_parser.add_argument('--purge', action="store_true")
    drop_parser.set_defaults(functor=drop)

    which_parser = subparsers.add_parser('env', help='Print the current environment name')
    which_parser.set_defaults(functor=env)

