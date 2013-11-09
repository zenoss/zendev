#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
import argcomplete
import subprocess

import py

from .log import error
from .config import get_config
from .repo import Repository
from .utils import colored
from .manifest import Manifest
from .environment import ZenDevEnvironment, get_config_dir, init_config_dir
from .environment import NotInitialized


def get_envname():
    return get_config().current


def check_env(name=None):
    envname = name or get_envname()
    if envname is None:
        error("Not in a zendev environment. Run 'zendev init' or 'zendev use'.")
        sys.exit(1)
    try:
        return ZenDevEnvironment(envname)
    except NotInitialized:
        error("Not a zendev environment. Run 'zendev init' first.")
        sys.exit(1)


def repofilter(repos=()):
    """
    Create a function that will return only those repos specified, or all if
    nothing was specified.
    """
    patterns = [re.compile(r, re.I) for r in repos]
    def filter_(repo):
        if repos:
            return any(p.search(repo.name) for p in patterns)
        return True
    return filter_


def init(args):
    """
    Initialize an environment.
    """
    path = py.path.local().ensure(args.path, dir=True)
    name = args.path  # TODO: Better name-getting
    config = get_config()
    config.add(name, args.path)
    with path.as_cwd():
        try:
            env = ZenDevEnvironment(path=path)
        except NotInitialized:
            init_config_dir()
            env = ZenDevEnvironment(path=path)
        env.initialize()
    env.use()


def add(args):
    """
    Add a manifest.
    """
    manifest = check_env().manifest
    manifest.merge(Manifest(args.manifest))
    manifest.save()


def remove(args):
    """
    Remove a repository.
    """
    env = check_env()
    if not args.repos:
        error("No repositories were specified.")
        sys.exit(1)
    env.remove(args.repofilter)


def freeze(args):
    """
    Output JSON representation of manifests.
    """
    print check_env().freeze()


def ls(args):
    """
    Output information about repositories.
    """
    config = get_config()
    cur = get_envname()
    for env in config.environments:
        prefix = colored('*', 'blue') if env==cur else ' '
        print prefix, env


def dir_(args):
    """
    Print the directory of the repository if specified or the environment if not.
    """
    if args.repo:
        repos = check_env().repos(repofilter([args.repo]))
        if not repos:
            error("No repo matching %s found" % args.repo)
            sys.exit(1)
        print repos[0].path.strpath
    else:
        print check_env()._root.strpath


def sync(args):
    """
    Clone or update any existing repositories, push any commits.
    """
    check_env().sync(args.repofilter)


def status(args):
    """
    Print status.
    """
    if args.repos:
        filter_ = args.repofilter
    elif args.all:
        filter_ = None
    else:
        filter_ = lambda r:any(r.changes)
    check_env().status(filter_)


def each(args):
    """
    Execute a command in each repo's directory.
    """
    for repo in ZenDevEnvironment().repos(args.repofilter):
        print repo.name
        with repo.path.as_cwd():
            subprocess.call(args.command, shell=True)


def use(args):
    """
    Use a zendev environment.
    """
    check_env(args.name).use()


def drop(args):
    """
    Drop a zendev environment.
    """
    get_config().remove(args.name, not args.purge)


def add_repo_narg(parser):
    parser.add_argument('repos', nargs='*')


def parse_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('path', metavar="PATH")
    init_parser.set_defaults(functor=init)

    use_parser = subparsers.add_parser('use')
    use_parser.add_argument('name', metavar='ENVIRONMENT')
    use_parser.set_defaults(functor=use)

    drop_parser = subparsers.add_parser('drop')
    drop_parser.add_argument('name', metavar='ENVIRONMENT')
    drop_parser.add_argument('--purge', action="store_true")
    drop_parser.set_defaults(functor=drop)

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    rm_parser = subparsers.add_parser('rm')
    add_repo_narg(rm_parser)
    rm_parser.set_defaults(functor=remove)

    ls_parser = subparsers.add_parser('ls')
    ls_parser.set_defaults(functor=ls)

    dir_parser = subparsers.add_parser('dir')
    dir_parser.add_argument('repo', nargs='?', metavar="REPO")
    dir_parser.set_defaults(functor=dir_)

    freeze_parser = subparsers.add_parser('freeze')
    freeze_parser.set_defaults(functor=freeze)

    sync_parser = subparsers.add_parser('sync')
    add_repo_narg(sync_parser)
    sync_parser.set_defaults(functor=sync)

    status_parser = subparsers.add_parser('status')
    status_parser.add_argument('-a', '--all', action='store_true', 
        help="Display all repos, whether or not they have changes.")
    add_repo_narg(status_parser)
    status_parser.set_defaults(functor=status)

    each_parser = subparsers.add_parser('each')
    add_repo_narg(each_parser)
    each_parser.add_argument('-c', dest="command")
    each_parser.set_defaults(functor=each)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    if hasattr(args, 'repos'):
        args.repofilter = repofilter(args.repos)
    return args



def main():
    args = parse_args()
    args.functor(args)


if __name__ == "__main__":
    main()
