#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import argcomplete



def add(args):
    """
    Add a manifest.
    """
    manifest = args.manifest
    Manifest(manifest)


def parse_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    argcomplete.autocomplete(parser)

    return parser.parse_args()


def main():
    args = parse_args()
    args.functor(args)


if __name__ == "__main__":
    main()
