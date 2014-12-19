from ..utils import add_repo_narg


def feature_start(args, env):
    """
    Start git flow feature for all requested repositories.
    """
    filter_ = None
    if args.repos:
        filter_ = args.repofilter
    env().start_feature(args.name, filter_)


def feature_list(args, env):
    """
    List git flow feature for all repositories.
    """
    env().list_feature(args.name)


def feature_pull(args, env):
    """
    Request github pull-request for repositories with feature name
    """
    filter_ = None
    if args.repos:
        filter_ = args.repofilter
    env().pull_feature(args.name, filter_)


def feature_finish(args, env):
    """
    finish all git repositories with feature name
    """
    filter_ = None
    if args.repos:
        filter_ = args.repofilter
    env().finish_feature(args.name, filter_)


def add_commands(subparsers):
    feature_parser = subparsers.add_parser('feature', help='Manage feature branches')
    feature_subparser = feature_parser.add_subparsers()

    feature_start_parser = feature_subparser.add_parser('start', help='Start feature branch on specified '
                                                                      'repositories')
    feature_start_parser.add_argument('name', help='Name of the feature branch')
    add_repo_narg(feature_start_parser)
    feature_start_parser.set_defaults(functor=feature_start)

    feature_start_parser = feature_subparser.add_parser('list', help="List all repos containing the specified "
                                                                     "feature branch")
    feature_start_parser.add_argument('name', help='Name of the feature branch')
    feature_start_parser.set_defaults(functor=feature_list)

    feature_pull_parser = feature_subparser.add_parser('pull', help="Create pull request for feature branch")
    feature_pull_parser.add_argument('name', help='Name of the feature branch')
    add_repo_narg(feature_pull_parser)
    feature_pull_parser.set_defaults(functor=feature_pull)

    feature_finish_parser = feature_subparser.add_parser('finish', help='Finish the feature branch')
    feature_finish_parser.add_argument('name', help="Name of the feature branch")
    add_repo_narg(feature_finish_parser)
    feature_finish_parser.set_defaults(functor=feature_finish)

