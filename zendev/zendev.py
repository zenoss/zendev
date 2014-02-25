#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

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
from .utils import colored, here
from .manifest import Manifest
from .environment import ZenDevEnvironment, get_config_dir, init_config_dir
from .environment import NotInitialized
from .box import BOXES


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


def bootstrap(args):
    print here("bootstrap.sh").strpath


def root(args):
    env = check_env()
    print env.root.strpath


def resetserviced(args):
    cmd = [here("resetserviced.sh").strpath]
    if args.root:
        cmd.insert(0, "GOBIN=" + os.environ["GOBIN"])
        cmd.insert(0, "GOPATH=" + os.environ["GOPATH"])
        cmd.insert(0, "sudo")
    subprocess.call(cmd)


def feature_start(args):
    """
    Start git flow feature for all requested repositories.
    """
    filter_ = None
    if args.repos:
    	  filter_ = args.repofilter
    check_env().start_feature(args.name, filter_)


def feature_list(args):
    """
    List git flow feature for all repositories.
    """
    check_env().list_feature(args.name)


def feature_pull(args):
    """
    Request github pull-request for repositories with feature name
    """
    filter_ = None
    if args.repos:
    	  filter_ = args.repofilter
    check_env().pull_feature(args.name, filter_)


def feature_finish(args):
    """
    finish all git repositories with feature name
    """
    filter_ = None
    if args.repos: filter_ = args.repofilter
    check_env().finish_feature(args.name, filter_)


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
    if args.default_repos:
        args.manifest = env.root.join('build/manifests').listdir()


def add(args, paths=()):
    """
    Add a manifest.
    """
    manifest = check_env().manifest
    for manifestpath in args.manifest or ():
        manifest.merge(Manifest(manifestpath))
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


def box_create(args):
    """
    """
    env = check_env()
    env.vagrant.create(args.name, args.type)
    env.vagrant.provision(args.name, args.type)
    env.vagrant.ssh(args.name)


def box_remove(args):
    env = check_env()
    env.vagrant.remove(args.name)


def box_ssh(args):
    check_env().vagrant.ssh(args.name)


def box_up(args):
    check_env().vagrant.up(args.name)


def box_halt(args):
    check_env().vagrant.halt(args.name)


def box_ls(args):
    check_env().vagrant.ls()


def cd(args):
    """
    Print the directory of the repository if specified or the environment if not.
    """
    env = check_env()
    if args.repo:
        repos = check_env().repos(repofilter([args.repo]))
        if not repos:
            error("No repo matching %s found" % args.repo)
            sys.exit(1)
        env.bash('cd "%s"' % repos[0].path.strpath)
    else:
        env.bash('cd "%s"' % env._root.strpath)


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

def build(args):
    with check_env().buildroot.as_cwd():
        target = 'srcbuild' if args.target == 'src' else args.target
        subprocess.call(["make", target])


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

    parser.add_argument('--script', action='store_true',
            help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers()

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('path', metavar="PATH")
    init_parser.add_argument('-d', '--default-repos', dest="default_repos",
            action="store_true")
    init_parser.set_defaults(functor=init)

    use_parser = subparsers.add_parser('use')
    use_parser.add_argument('name', metavar='ENVIRONMENT')
    use_parser.set_defaults(functor=use)

    build_parser = subparsers.add_parser('build')
    build_parser.add_argument('target', metavar='TARGET', 
            choices=['src', 'core', 'resmgr'])
    build_parser.set_defaults(functor=build)

    drop_parser = subparsers.add_parser('drop')
    drop_parser.add_argument('name', metavar='ENVIRONMENT')
    drop_parser.add_argument('--purge', action="store_true")
    drop_parser.set_defaults(functor=drop)

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', nargs='*', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    rm_parser = subparsers.add_parser('rm')
    add_repo_narg(rm_parser)
    rm_parser.set_defaults(functor=remove)

    ls_parser = subparsers.add_parser('ls')
    ls_parser.set_defaults(functor=ls)

    cd_parser = subparsers.add_parser('cd')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)

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

    #feature parser
    feature_parser = subparsers.add_parser('feature')
    feature_subparser = feature_parser.add_subparsers()

    feature_start_parser = feature_subparser.add_parser('start')
    feature_start_parser.add_argument('name')
    add_repo_narg(feature_start_parser)
    feature_start_parser.set_defaults(functor=feature_start)

    feature_start_parser = feature_subparser.add_parser('list')
    feature_start_parser.add_argument('name')
    feature_start_parser.set_defaults(functor=feature_list)

    feature_pull_parser = feature_subparser.add_parser('pull')
    feature_pull_parser.add_argument('name')
    add_repo_narg(feature_pull_parser)
    feature_pull_parser.set_defaults(functor=feature_pull)

    feature_finish_parser = feature_subparser.add_parser('finish')
    feature_finish_parser.add_argument('name')
    add_repo_narg(feature_finish_parser)
    feature_finish_parser.set_defaults(functor=feature_finish)

    each_parser = subparsers.add_parser('each')
    add_repo_narg(each_parser)
    each_parser.add_argument('-c', dest="command")
    each_parser.set_defaults(functor=each)

    box_parser = subparsers.add_parser('box')
    box_subparsers = box_parser.add_subparsers()

    box_create_parser = box_subparsers.add_parser('create')
    box_create_parser.add_argument('name', metavar="NAME")
    box_create_parser.add_argument('--type', required=True, choices=BOXES)
    box_create_parser.set_defaults(functor=box_create)

    box_up_parser = box_subparsers.add_parser('up')
    box_up_parser.add_argument('name', metavar="NAME")
    box_up_parser.set_defaults(functor=box_up)

    box_halt_parser = box_subparsers.add_parser('halt')
    box_halt_parser.add_argument('name', metavar="NAME")
    box_halt_parser.set_defaults(functor=box_halt)

    box_remove_parser = box_subparsers.add_parser('destroy')
    box_remove_parser.add_argument('name', metavar="NAME")
    box_remove_parser.set_defaults(functor=box_remove)

    box_ssh_parser = box_subparsers.add_parser('ssh')
    box_ssh_parser.add_argument('name', metavar="NAME")
    box_ssh_parser.set_defaults(functor=box_ssh)

    box_ls_parser = box_subparsers.add_parser('ls')
    box_ls_parser.set_defaults(functor=box_ls)

    ssh_parser = subparsers.add_parser('ssh')
    ssh_parser.add_argument('name', metavar="NAME")
    ssh_parser.set_defaults(functor=box_ssh)

    bootstrap_parser = subparsers.add_parser('bootstrap')
    bootstrap_parser.set_defaults(functor=bootstrap)

    root_parser = subparsers.add_parser('root')
    root_parser.set_defaults(functor=root)

    serviced_parser = subparsers.add_parser('resetserviced')
    serviced_parser.add_argument('--root', action='store_true',
        help="run resetserviced as root")
    serviced_parser.set_defaults(functor=resetserviced)


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
