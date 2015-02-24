import json
import py
import zendev.github as github
import zendev.log

from git.exc import GitCommandError
from gitflow.exceptions import GitflowError, BranchExistsError


class GithubException (Exception):
    pass


def pullrequest_commit(repo, pr):
    url = '/repos/%s/issues/%s/events' % (repo.reponame, pr)
    headers, response = github.perform('GET', url)

    if headers['status'] !=  "200 OK":
        raise GithubException("Error looking up pull request #%s on %s: %s" %
                              (pr, repo.reponame, headers['status']))

    # TODO: this needs some error checking...
    commit_shas = [event['commit_id'] for event in response if event['event'] == 'merged']

    # TODO: Need to make sure that '1' is the correct parent.
    # TODO: Look in the list of commits in the PR to see which is parent is the base.
    return commit_shas[0], 1


def get_current_repo(env):
    # Get repo for cwd
    cwd = py.path.local().strpath
    repos = env().repos(lambda x: cwd.startswith(x.path.strpath))
    if len(repos) == 1:
        return repos[0]
    else:
        zendev.log.error("Could not determine repo for '%s'" % cwd)
        exit(1)


def create_branch(repo, base, name):
    # Create a new branch for the port
    try:
        zendev.log.info("Creating branch feature/%s from %s" % (name, base))
        repo.start_feature(name, base)
        zendev.log.info("Checkout feature/%s " % name)
        return 'feature/%s' % name
    except BranchExistsError as e:
        zendev.log.error("Branch exists: %s" % e)
        exit(1)
    except GitflowError as e:
        zendev.log.error(e)
        exit(1)

    
def cherry_pick(repo, commit):
    if commit.startswith('#'):
        try:
            commit_sha, parent = pullrequest_commit(repo, commit[1:])
            cherry_pick_args = [commit_sha, '-m%d' % parent]
        except GithubException as e:
            zendev.log.error(e)
            exit(1)
    else:
        cherry_pick_args = [commit]

    zendev.log.info("Cherry picking commits into %s" % repo.branch)
    try:
        repo.repo.git.cherry_pick('-x', *cherry_pick_args)
    except GitCommandError as e:
        zendev.log.error(e)
        exit(1)


def create_pull_request(repo, head, base, commit):
    zendev.log.info('Creating pull request for branch "%s" into "%s"' %
                    (head, base))
    repo.create_pull_request(head, base=base, 
                             body='zendev cherry-pick %s' % commit)


def port_start(args, env):
    repo = get_current_repo(env)
    create_branch(repo, repo.branch, args.ticket)

def port_pick(args, env):
    repo = get_current_repo(env)
    cherry_pick(repo, args.commit)

def port_pull_request(args, env):
    repo = get_current_repo(env)
    # TODO: pull base and actions from a config file in .git directory
    base = 'master'
    actions = '#3'

    # TODO: is this the best way to determine the feature name?
    branch = repo.branch.split('/')[1]
    create_pull_request(repo, branch, base, actions)
    

def port_try(args, env):
    repo = get_current_repo(env)
    base_branch = repo.branch
    feature_branch = create_branch(repo, base_branch, args.ticket)
    cherry_pick(repo, args.commit)
    create_pull_request(repo, feature_branch, base_branch, args.commit)


def add_commands(subparsers):
    port_help='Cherry-pick a fix into a branch'
    port_description = ("In the current git repo, create a feature "
        "branch from the ticket name, cherry-pick a commit, and "
        "submit a pull request.")
    port_parser = subparsers.add_parser('port', help=port_help,
                                            description=port_description)
    port_subparser = port_parser.add_subparsers()

    start_parser = port_subparser.add_parser('start',
        help='Start port branch from current branch in current repository')
    start_parser.add_argument('ticket', help='Ticket this fix applies to')
    start_parser.set_defaults(functor=port_start)

    pick_parser = port_subparser.add_parser('cherry-pick',
        help='Cherry-pick commit or PR into current branch')
    pick_parser.add_argument('commit',
                             help='Pull request (e.g. #123) or commit hash')
    pick_parser.set_defaults(functor=port_pick)

    pull_parser = port_subparser.add_parser('pull-request',
        help='Create pull request for current branch')
    pull_parser.set_defaults(functor=port_pull_request)

    try_parser = port_subparser.add_parser('try',
        help='Do all: start, pick, pull-request')
    try_parser.add_argument('ticket', help='Ticket this fix applies to')
    try_parser.add_argument('commit',
                            help='Pull request (e.g. #123) or commit hash')
    try_parser.set_defaults(functor=port_pull_request)
    try_parser.set_defaults(functor=port_try)




