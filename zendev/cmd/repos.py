import os
import subprocess
import sys

import py

from ..log import error
from ..manifest import create_manifest
from ..config import get_config, get_envname
from ..utils import colored, add_repo_narg, repofilter


def add(args, env):
    """
    Add a manifest.
    """
    manifest = env().manifest
    manifest.merge(create_manifest(args.manifest or ()))
    manifest.save()


def addrepo(args, env):
    """
    Add a repo
    """

    if not args.repository:
        error("No repository was specified.")
        sys.exit(1)

    if not args.path:
        error("No path was specified.")
        sys.exit(1)


    manifest = env().manifest
    manifest.add(args.path, args.repository, args.ref)
    manifest.save()


def remove(args, env):
    """
    Remove a repository.
    """
    if not args.repos:
        error("No repositories were specified.")
        sys.exit(1)
    env().remove(args.repofilter)


def freeze(args, env):
    """
    Output JSON representation of manifests.
    """
    print env().freeze()


def ls(args, env):
    """
    Output information about repositories.
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


def sync(args, env):
    """
    Clone or update any existing repositories, push any commits.
    """
    env().sync(args.repofilter)


def status(args, env):
    """
    Print status.
    """
    if args.repos:
        filter_ = args.repofilter
    elif args.all:
        filter_ = None
    else:filter_ = lambda r: not r.path.check() or any(r.changes)
    env().status(filter_)


def each(args, env):
    """
    Execute a command in each repo's directory.
    """
    for repo in env().repos(args.repofilter):
        print repo.name
        try:
            with repo.path.as_cwd():
                subprocess.call(args.command)
        except py.error.ENOENT:
            error('%s is missing. Try "zendev sync" first.' % repo.name)


def cd(args, env):
    """
    Print the directory of the repository if specified or the environment if
    not.
    """
    env = env()
    if args.repo:
        repos = env.repos(repofilter([args.repo]))
        if not repos:
            # try to fall back to a directory in our srcroot
            nonRepoPath = env.srcroot.join(args.repo).strpath
            if os.path.isdir(nonRepoPath):
                env.bash('cd "%s"' % nonRepoPath)
                return
            else:
                error("No repo matching %s found" % args.repo)
                sys.exit(1)
        for repo in repos:
            if repo.path.strpath.endswith(args.repo.strip()):
                env.bash('cd "%s"' % repo.path.strpath)
                return
        env.bash('cd "%s"' % repos[0].path.strpath)
    else:
        env.bash('cd "%s"' % env._root.strpath)


def add_commands(subparsers):

    add_parser = subparsers.add_parser('add', help='Add repos in a manifest to environment')
    add_parser.add_argument('manifest', nargs='+', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    addrepo_parser = subparsers.add_parser('addrepo', help='Add repos to environment')
    addrepo_parser.add_argument('path', help="Path to Source")
    addrepo_parser.add_argument('repository', help="Repository in github")
    addrepo_parser.add_argument('ref', nargs="?",
                                default='develop', help="git ref or branch name")
    addrepo_parser.set_defaults(functor=addrepo)

    rm_parser = subparsers.add_parser('rm', help='Remove repo from environment')
    add_repo_narg(rm_parser)
    rm_parser.set_defaults(functor=remove)

    ls_parser = subparsers.add_parser('ls', help='List environments')
    ls_parser.set_defaults(functor=ls)

    freeze_parser = subparsers.add_parser('freeze', help='Generate manifest from current repository state')
    freeze_parser.set_defaults(functor=freeze)

    sync_parser = subparsers.add_parser('sync', help='Clone or update repositories; push commits')
    add_repo_narg(sync_parser)
    sync_parser.set_defaults(functor=sync)

    status_parser = subparsers.add_parser('status', help='Show status of repos')
    status_parser.add_argument('-a', '--all', action='store_true',
               help="Display all repos, whether or not they have changes.")
    add_repo_narg(status_parser)
    status_parser.set_defaults(functor=status)

    each_parser = subparsers.add_parser('each', help='Execute a command in each repo\'s directory.', usage='%(prog)s <command> [-r|--repo [REPO [REPO ...]]]')
    each_parser.add_argument('-r', '--repo', dest="repos", nargs='*')
    each_parser.add_argument('command', nargs="+")
    each_parser.set_defaults(functor=each)

    cd_parser = subparsers.add_parser('cd', help='Change working directory to a repo')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)
