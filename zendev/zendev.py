import argcomplete
import argparse
import subprocess
import sys
import textwrap
from .utils import here, colored

from .environment import ZenDevEnvironment
from .environment import NotInitialized

from .cmd import build, devimg, environment, serviced, tags

from .config import get_config, get_envname
from .log import error

def parse_args():
    epilog = textwrap.dedent('''
    Environment commands: {init, use, drop, env}
    Serviced commands: {serviced, atttach, devshel}
    ''')

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog)

    subparsers = parser.add_subparsers(dest='subparser')

    bootstrap_parser = subparsers.add_parser('bootstrap', help='Bootstrap zendev to modify the shell environment')
    bootstrap_parser.set_defaults(functor=bootstrap)

    root_parser = subparsers.add_parser('root', help='Print root directory of the current environment')
    root_parser.set_defaults(functor=root)

    ls_parser = subparsers.add_parser('ls', help='List environments')
    ls_parser.set_defaults(functor=ls)

    update_parser = subparsers.add_parser('selfupdate', help='Update zendev')
    update_parser.set_defaults(functor=selfupdate)

    # Add sub commands here
    environment.add_commands(subparsers)
    tags.add_commands(subparsers, tagsCompleter)
    build.add_commands(subparsers)
    devimg.add_commands(subparsers)
    serviced.add_commands(subparsers)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    return args


def selfupdate(args, env):
    with here().as_cwd():
        subprocess.call(["git", "pull"])


def root(args, env):
    print env().root.strpath


def bootstrap(args, env):
    print here("bootstrap.sh").strpath


def tagsCompleter(prefix, **kwargs):
    return (x for x in check_env().list_tags() if x.startswith(prefix))


def ls(args, env):
    """
    Output information about environments.
    """
    config = get_config()
    cur = get_envname()
    for env in config.environments:
        prefix = colored('*', 'blue') if env == cur else ' '
        envDetails =  config.environments[env]
        suffix = '(v1)'
        if 'version' in envDetails:
            suffix = '(%s)' % envDetails['version']
        print prefix, env, suffix

def check_env(name=None, **kwargs):
    envname = name or get_envname()
    if envname is None:
        error("Not in a zendev environment. Run 'zendev init' or 'zendev use'.")
        sys.exit(1)
    if not get_config().exists(envname):
        error("Zendev environment %s does not exist." % envname)
        sys.exit(1)

    try:
        return ZenDevEnvironment(envname, **kwargs)
    except NotInitialized:
        error("Not a zendev environment. Run 'zendev init' first.")
        sys.exit(1)

#
# A whitelist of all of commands which are allowed in all implementations of zendev.
#
all_env_whitelist = [
    "bootstrap",
    "env",
    "init,"
    "ls",
    "root",
    "selfupdate",
    "use"
]

def validate_cmd_env(args):
    if any(args.subparser in s for s in all_env_whitelist):
        return True
    config = get_config()
    return config.validate(config.current)

def main():
    args = parse_args()
    if not validate_cmd_env(args):
        sys.exit(1)

    args.functor(args, check_env)


if __name__ == "__main__":
    main()
