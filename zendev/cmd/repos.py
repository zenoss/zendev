import subprocess
import sys

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
        print prefix, env


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
    else:
        filter_ = lambda r: not r.path.check() or any(r.changes)
    env().status(filter_)


def each(args, env):
    """
    Execute a command in each repo's directory.
    """
    for repo in env().repos(args.repofilter):
        print repo.name
        with repo.path.as_cwd():
            subprocess.call(args.command)


def cd(args, env):
    """
    Print the directory of the repository if specified or the environment if not.
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

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', nargs='+', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    rm_parser = subparsers.add_parser('rm')
    add_repo_narg(rm_parser)
    rm_parser.set_defaults(functor=remove)

    ls_parser = subparsers.add_parser('ls')
    ls_parser.set_defaults(functor=ls)

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
    each_parser.add_argument('-r', '--repo', dest="repos", nargs='*')
    each_parser.add_argument('command', nargs="*")
    each_parser.set_defaults(functor=each)

    cd_parser = subparsers.add_parser('cd')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)


