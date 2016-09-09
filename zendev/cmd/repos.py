import os
import subprocess

from ..log import error
from ..utils import repofilter

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

def status(args, env):
    jigCmd = ['jig', 'status']
    if args.all:
        jigCmd.append('-a')
    if args.verbose:
        jigCmd.append('-v')
    subprocess.check_call(jigCmd)

def pull(args, env):
    jigCmd = ['jig', 'pull']
    if args.verbose:
        jigCmd.append('-v')
    subprocess.check_call(jigCmd)

def add_commands(subparsers):
    cd_parser = subparsers.add_parser('cd', help='Change working directory to a repo')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)

    status_parser = subparsers.add_parser('status', help='Show the status of current repos')
    status_parser.add_argument('-a', '--all', action="store_true", help="show all repos, not just changed repos")
    status_parser.add_argument('-v', '--verbose', action="store_true")
    status_parser.set_defaults(functor=status)

    pull_parser = subparsers.add_parser('pull', help='Pull latest changes for all repos')
    pull_parser.add_argument('-v', '--verbose', action="store_true")
    pull_parser.set_defaults(functor=pull)
