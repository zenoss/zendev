import re
import sys

from pprint import pprint
from termcolor import colored
import gitflow.core
import py
import github
import time
import json

from .log import error, info
from .utils import is_git_repo, memoize


is_github = re.compile('^[^\/\s@]+\/[^\/\s]+$').match


class Repository(object):
    """
    A repository.
    """
    def __init__(self, localname, path, repo, ref="develop"):
        self.name = localname
        self.path = py.path.local(path)
        self.reponame = str(repo)
        self.url = self._proper_url(repo)
        self.ref = ref
        self.progress = None
        self._repo = None

    def _proper_url(self, url):
        if is_github(url):
            return 'git@github.com:' + url
        return url

    @property
    @memoize
    def branch(self):
        return self.repo.repo.active_branch.name

    @property
    @memoize
    def remote_branch(self):
        tracking = self.repo.repo.active_branch.tracking_branch()
        if tracking:
            return tracking.name

    @property
    @memoize
    def remote_branches(self):
        """ return a list of all remote branches """
        return self.repo.branch_names(remote=True)

    @property
    @memoize
    def local_branches(self):
        """ return a list of all local branches """
        return self.repo.branch_names()

    @property
    @memoize
    def changes(self):
        staged = unstaged = untracked = False
        output = self.repo.repo.git.status(porcelain=True)
        lines = self.repo.repo.git.status('-z', porcelain=True).split('\x00')
        for char in (x[:2] for x in lines):
            if char.startswith('?'):
                untracked = True
            elif char.startswith(' '):
                unstaged = True
            elif char:
                staged = True
        return staged, unstaged, untracked

    @property
    @memoize
    def repo(self):
        self.initialize()
        return self._repo


    def clone(self, shallow=False):
        kwargs = {}
        if shallow:
            kwargs['depth'] = 1
        if self.ref:
            kwargs['branch'] = self.ref
        if self.path.check():
            raise Exception("Something already exists at %s. "
                    "Remove it first." % self.path)
        else:
            self.path.dirpath().ensure(dir=True)
            gitrepo = gitflow.core.Repo.clone_from(
                    self.url, 
                    str(self.path), 
                    progress=self.progress,
                    **kwargs)
            self._repo = gitflow.core.GitFlow(gitrepo)
            if not shallow:
                self.initialize()

    def shallow_clone(self):
        return self.clone(shallow=True)

    def start_feature(self, name):
        self.repo.create('feature', name, None, None)

    def publish_feature(self, name):
        self.repo.publish('feature', name)

    def finish_feature(self, name):
        feature_name = "feature/%s" % name
        origin_feature_name = "origin/feature/%s" % name

        if feature_name in self.local_branches:
          self.repo.finish( 'feature', name,
              fetch=True, rebase=False, keep=False,
              force_delete=True, tagging_info=None)

        #XXX repo (GitFlow) doesn't push remote repo delete currently :(
        if origin_feature_name in self.remote_branches:
          self.repo.origin().push( ":" + feature_name)

    def stash(self):
        self.repo.git.stash( )

    def apply_stash(self):
        self.repo.git.stash( 'apply')

    def fetch(self):
        self.repo.git.fetch(all=True)

    def message(self, msg):
        print colored('==>', 'blue'), colored(msg, 'white')

    def merge_from_remote(self):
        active_branch = self.repo.repo.active_branch
        local_name = active_branch.name
        tracking = active_branch.tracking_branch()
        remote_name = tracking.name if tracking else local_name

        if self.repo.is_merged_into(remote_name, local_name):
            # Nothing to do
            return
        self.message("Changes found in %s:%s! Rebasing %s..." % (
            self.name, remote_name, local_name))
        self.repo.git.rebase(remote_name, output_stream=sys.stderr)

    def push(self):
        active_branch = self.repo.repo.active_branch
        local_name = active_branch.name
        output = self.repo.git.rev_list(local_name, '--not', '--remotes')
        if output:
            self.message(
                    "%s local commits in %s:%s need to be pushed. Pushing..." % (
                output.count('\n')+1, self.name, local_name))
            self.repo.git.push(output_stream=sys.stderr)

    def create_feature(self, name):
        fname = "feature/%s" % name
        ofname = "origin/feature/%s" % name

        local = fname in self.local_branches
        remote = ofname in self.remote_branches

        if local and remote:
            return

        if not local and remote:
            self.fetch()
        elif local and not remote:
            self.publish_feature( name)
        else:
            self.start_feature( name)
            self.publish_feature( name)


    def create_pull_request(self, feature_name, body=''):
        staged, unstaged, untracked = self.changes

        if unstaged:
          error( "uncommited changes in: %s" % self.name)
          return

        branch = "feature/%s" % feature_name
        url = self.repo.repo.remote().url
        line = url.rsplit(":", 1)[-1]
        owner, repo = line.split('/')[-2:]
        repo = repo.split()[0]
        if repo.endswith('.git'):
            repo= repo[:-4]

        self.push()
        time.sleep(1)
        response = github.perform(
            "POST",
            "/repos/{0}/{1}/pulls".format(owner, repo),
            data=json.dumps({
                "title": "Please review branch %s" % branch,
                "body": body,
                "head": branch,
                "base": "develop"
            }))
        if 'html_url' in response:
            info ("Pull Request: %s" % response['html_url'])
        elif response['message'] == 'Validation Failed':
            for e in response['errors']:
                if e ['message'].startswith("No commits between"):
                    error("You have to commit some code first!")
                    return
                else:
                    error("You have to commit some code first!")
                    error( e.get('message'))

    def initialize(self):
        if not self._repo and is_git_repo(self.path):
            self._repo = gitflow.core.GitFlow(self.path.strpath)
        if self._repo and not self._repo.is_initialized():
            py.io.StdCaptureFD.call(self._repo.init)
