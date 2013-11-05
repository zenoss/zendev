#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
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


def init(args):
    """
    Initialize an environment.
    """
    try:
        env = ZenDevEnvironment()
    except NotInitialized:
        init_config_dir()
    else:
        print "You're already in an environment."
        sys.exit(1)


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
    ZenDevEnvironment().sync()


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
    sync_parser.set_defaults(functor=sync)

    argcomplete.autocomplete(parser)

    return parser.parse_args()


def main():
    args = parse_args()
    args.functor(args)


if __name__ == "__main__":
    main()
