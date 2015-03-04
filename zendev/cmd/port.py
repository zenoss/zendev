import json
import os
import py
import zendev.github as github
import zendev.log

from contextlib import contextmanager
from git.exc import GitCommandError
from gitflow.exceptions import GitflowError, BranchExistsError


class GithubException (Exception):
    pass

@contextmanager
def env_var(key, value):
    tmp = os.environ.get(key)
    os.environ[key] = value
    yield
    if tmp != None:
        os.environ[key]=tmp
    else:
        del os.environ[key]


def get_portinfo_filename(repo, branch):
    return repo.path.join('.git', 'zendev', 'port', branch)


def save_portinfo_base(repo, base, branch):
    data = {'base':base, 'message':[]}
    filename = get_portinfo_filename(repo, branch).ensure()
    json.dump(data, open(filename.strpath, 'w'), indent=4)


def load_portinfo(repo, branch):
    filename = get_portinfo_filename(repo, branch)
    try:
        return json.load(open(filename.strpath, 'r'))
    except:
        return {}


def save_portinfo_message(repo, branch, comment):
    data = load_portinfo(repo, branch)
    data.setdefault('message', []).append(comment)
    filename = get_portinfo_filename(repo, branch)
    json.dump(data, open(filename.strpath, 'w'), indent=4)


def pullrequest_commit(repo, pr):
    """
    Given a pull request, get the merge commit and the index of the base parent
    """
    url = '/repos/%s/issues/%s/events' % (repo.reponame, pr)
    headers, response = github.perform('GET', url)
    if headers['status'] !=  "200 OK":
        raise GithubException("Error looking up pull request #%s on %s: %s" %
                              (pr, repo.reponame, headers['status']))
    commit_shas = [event['commit_id'] for event in response if event['event'] == 'merged']
    if len(commit_shas) == 0:
        zendev.log.error('Pull-request "%s" not merged', pr)
        exit(1)
    elif len(commit_shas) > 1 :
        zendev.log.error('Multiple merges for pull-request "%s"', pr)
        exit(1)
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

    
def cherry_pick(repo, branch, commit):
    for prefix in ('#', 'pull/'):
        if commit.startswith(prefix):
            pr = commit[len(prefix):]
            try:
                int(pr)
            except ValueError:
                zendev.log.error('Pull-request must be an integer: %s' % commit)
                exit(1)
            break
    else:
        pr = None

    if pr != None:
        try:
            commit_sha, parent = pullrequest_commit(repo, pr)
            cherry_pick_args = [commit_sha, '-m%d' % parent]
            commit_msg = "cherry-pick pull-request #%s" % pr
        except GithubException as e:
            zendev.log.error(e)
            exit(1)
    else:
        cherry_pick_args = [commit]
        commit_msg = "cherry-pick commit %s" % commit

    commit_msg = 'Fixes %s\n\n%s\n(commited by "zendev port cherry-pick")' %\
                 (branch.split('/')[-1], commit_msg)

    zendev.log.info("Cherry picking commits into %s" % branch)
    try:
        with env_var('GIT_EDITOR', "echo '%s' >" % commit_msg):
            repo.repo.git.cherry_pick('-e', *cherry_pick_args)
    except GitCommandError as e:
        zendev.log.error(e)
        exit(1)


def create_pull_request(repo, feature_name, base, comments):
    zendev.log.info('Creating pull request for branch "feature/%s" into "%s"' %
                    (feature_name, base))
    body = '\n\n'.join(filter(None, (comments, 'Pull request created by zendev port')))
    repo.create_pull_request(feature_name, base=base, body=body)


def port_start(args, env):
    repo = get_current_repo(env)
    base = repo.branch
    feature_branch = create_branch(repo, base, args.ticket)
    save_portinfo_base(repo, base, feature_branch)


def port_pick(args, env):
    repo = get_current_repo(env)
    cherry_pick(repo, repo.branch, args.commit)
    save_portinfo_message(repo, repo.branch, "Cherry-picked %s" % args.commit)


def port_pull_request(args, env):
    repo = get_current_repo(env)
    data = load_portinfo(repo, repo.branch)
    base = args.branch or data.get('base')
    if not base:
        zendev.log.error('Specify merge target with "--branch"')
        exit(1)
    comments = '\n'.join(filter(None, [args.message]+data.get('message', [])))
    # TODO: is this the best way to determine the feature name?
    ticket = repo.branch.split('/')[-1]
    create_pull_request(repo, ticket, base, comments)


def port_do(args, env):
    repo = get_current_repo(env)
    base_branch = args.branch or repo.branch
    feature_branch = create_branch(repo, base_branch, args.ticket)
    save_portinfo_base(repo, base_branch, feature_branch)
    cherry_pick(repo, feature_branch, args.commit)
    create_pull_request(repo, args.ticket, base_branch, "Cherry-picked %s" % args.commit)


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
                             help='Pull request (e.g. #123, pull/123) or commit hash')
    pick_parser.set_defaults(functor=port_pick)

    pull_parser = port_subparser.add_parser('pull-request',
        help='Create pull request for current branch')
    pull_parser.add_argument('-b', '--branch',
                             help="branch to merge into")
    pull_parser.add_argument('-m', '--message', default='',
                             help="message for pull-request")
    pull_parser.set_defaults(functor=port_pull_request)

    do_parser = port_subparser.add_parser('do',
        help='Do all: start, pick, pull-request')
    do_parser.add_argument('ticket', help='Ticket this fix applies to')
    do_parser.add_argument('commit',
                            help='Pull request (e.g. #123, pull/123) or commit hash')
    do_parser.add_argument('-b', '--branch',
                             help="branch to merge into")
    do_parser.set_defaults(functor=port_do)




