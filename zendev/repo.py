import re
import sys

from termcolor import colored
import gitflow.core
import py

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
        return self.repo.repo.active_branch.tracking_branch().name

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

    def clone(self):
        if self.path.check():
            raise Exception("Something already exists at %s. "
                    "Remove it first." % self.path)
        else:
            self.path.dirpath().ensure(dir=True)
            gitrepo = gitflow.core.Repo.clone_from(
                    self.url, 
                    str(self.path), 
                    progress=self.progress)
            self._repo = gitflow.core.GitFlow(gitrepo)
            self.initialize()

    def fetch(self):
        self.repo.git.fetch(all=True)

    def message(self, msg):
        print colored('==>', 'blue'), colored(msg, 'white')

    def merge_from_remote(self):
        active_branch = self.repo.repo.active_branch
        remote_name = active_branch.tracking_branch().name
        local_name = active_branch.name

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

    def initialize(self):
        if not self._repo and is_git_repo(self.path):
            self._repo = gitflow.core.GitFlow(self.path.strpath)
        if self._repo and not self._repo.is_initialized():
            py.io.StdCaptureFD.call(self._repo.init)
