#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import argparse
import argcomplete

from .manifest import Manifest
from .environment import ZenDevEnvironment, get_config_dir, init_config_dir
from .environment import NotInitialized


def check_env():
    try:
        return ZenDevEnvironment()
    except NotInitialized:
        print "Error: not a zendev enviroment. Run 'zendev init' first."
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
    try:
        env = ZenDevEnvironment()
    except NotInitialized:
        init_config_dir()
        env = ZenDevEnvironment()
    env.initialize()


def add(args):
    """
    Add a manifest.
    """
    manifest = check_env().manifest
    manifest.merge(Manifest(args.manifest))
    manifest.save()


def freeze(args):
    """
    Output JSON representation of manifests.
    """
    print check_env().freeze()


def sync(args):
    """
    Clone or update any existing repositories, push any commits.
    """
    ZenDevEnvironment().sync(args.repofilter)


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
    ZenDevEnvironment().status(filter_)


def add_repo_narg(parser):
    parser.add_argument('repos', nargs='*')


def parse_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    init_parser = subparsers.add_parser('init')
    init_parser.set_defaults(functor=init)

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

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
