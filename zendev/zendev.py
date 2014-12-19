#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import os
import sys
import argparse
import subprocess
import textwrap
from contextlib import contextmanager

import argcomplete
import py

from .log import error
from .config import get_config, get_envname
from .utils import here, repofilter
from . import config as zcfg
from . import environment as zenv
from .environment import ZenDevEnvironment
from .environment import NotInitialized
from .cmd import box, cluster, serviced, feature, repos, tags, environment, build, test

class fargs(object):
    pass


@contextmanager
def temp_env():
    """
    Creates a temporary environment and patches everything to use it for the
    lifespan of the context manager.
    """
    td = py.path.local.mkdtemp()
    _old, zenv.CONFIG_DIR = zenv.CONFIG_DIR, td.join('config')
    _old, zcfg.CONFIG_DIR = zcfg.CONFIG_DIR, td.join('config')
    _zdebash, ZenDevEnvironment.bash = ZenDevEnvironment.bash, lambda *x: None
    path = td.join('root')
    args = fargs()
    args.path = path.strpath
    args.default_repos = False
    args.tag = None
    env = environment.init(args, check_env)
    os.environ.update(env.envvars())
    yield
    zenv.CONFIG_DIR = _old
    zcfg.CONFIG_DIR = _old
    ZenDevEnvironment.bash = _zdebash


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


def restoreCompleter(prefix, **kwargs):
    return (x for x in check_env().list_tags() if x.startswith(prefix))


def bootstrap(args, env):
    print here("bootstrap.sh").strpath


def root(args, env):
    print env().root.strpath


def selfupdate(args, env):
    with here().as_cwd():
        subprocess.call(["git", "pull"])



def parse_args():
    epilog = textwrap.dedent('''
    Management commands: {bootstrap, root, selfupdate}
    Environment commands: {init, use, drop, clone, env}
    Repo commands: {add, addrepo, rm, ls, freeze, sync, status, sync, cd}
    Tag commands: {restore, tag, changelog}
    Serviced commands: {serviced, atttach, devshel}
    Vagrant commands {box, cluster, ssh}
    ''')

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog)

    parser.add_argument('--script', action='store_true',
                        help=argparse.SUPPRESS)

    parser.add_argument('-n', '--noenv', action='store_true',
                        help="Run in a temporary environment")

    subparsers = parser.add_subparsers(dest='subparser')

    bootstrap_parser = subparsers.add_parser('bootstrap', help='Bootstrap zendev to modify the shell environment')
    bootstrap_parser.set_defaults(functor=bootstrap)

    root_parser = subparsers.add_parser('root', help='Print root directory of the current environment')
    root_parser.set_defaults(functor=root)

    update_parser = subparsers.add_parser('selfupdate', help='Update zendev')
    update_parser.set_defaults(functor=selfupdate)

    environment.add_commands(subparsers)
    repos.add_commands(subparsers)
    build.add_commands(subparsers)
    box.add_commands(subparsers)
    cluster.add_commands(subparsers)
    tags.add_commands(subparsers, restoreCompleter)
    feature.add_commands(subparsers)
    serviced.add_commands(subparsers)
    test.add_commands(subparsers)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Doing this here instead of in the functor because I want access to the
    # parser to properly throw the parsing error
    build_parser = parser._subparsers._group_actions[0].choices['build']
    if args.subparser == 'build':
        if (args.rps or args.ga_image) and not (args.rps and args.ga_image):
            build_parser.error("The --rps and --ga_image arguments must be used together")
            # Enforce using --rps with an rps-img-% target
        if (args.rps and not any(t.startswith('rps-img-') for t in args.target)) or \
                (not args.rps and any(t.startswith('rps-img-') for t in args.target)):
            build_parser.error("Must call an 'rps-img-%' target with the --rps arg")

    if hasattr(args, 'repos'):
        args.repofilter = repofilter(args.repos or ())

    return args


def main():
    args = parse_args()
    if args.noenv:
        with temp_env():
            args.functor(args, check_env)
    else:
        args.functor(args, check_env)


if __name__ == "__main__":
    main()
