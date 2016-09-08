import os
# import subprocess
# import sys

# import py

from ..log import error
# from ..config import get_config, get_envname
from ..utils import repofilter

# TODO: add pull and status

def cd(args, env):
    """
    Change to the directory of the repository if specified or the environment if
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
    cd_parser = subparsers.add_parser('cd', help='Change working directory to a repo')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)
