import subprocess


def status(args, env):
    env = env()
    jigCmd = ["jig", "status"]
    if args.all:
        jigCmd.append("-a")
    if args.verbose:
        jigCmd.append("-v")
    subprocess.check_call(jigCmd)


def pull(args, env):
    env = env()
    jigCmd = ["jig", "pull"]
    if args.verbose:
        jigCmd.append("-v")
    subprocess.check_call(jigCmd)


def add_commands(subparsers):
    status_parser = subparsers.add_parser(
        "status", help="Show the status of current repos"
    )
    status_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="show all repos, not just changed repos",
    )
    status_parser.add_argument("-v", "--verbose", action="store_true")
    status_parser.set_defaults(functor=status)

    pull_parser = subparsers.add_parser(
        "pull", help="Pull latest changes for all repos"
    )
    pull_parser.add_argument("-v", "--verbose", action="store_true")
    pull_parser.set_defaults(functor=pull)
