import re

import gitflow.core
import py

from .utils import is_git_repo
from .progress import GitProgress


is_github = re.compile('^[^\/\s@]+\/[^\/\s]+$').match


class Repository(object):
    """
    A repository.
    """
    def __init__(self, path, repo, ref="develop"):
        self.name = str(repo)
        self.path = py.path.local(path)
        self.url = self._proper_url(repo)
        self.ref = ref
        self.progress = None
        self._repo = None

    def _proper_url(self, url):
        if is_github(url):
            return 'git@github.com:' + url
        return url

    @property
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

    def initialize(self):
        if not self._repo and is_git_repo(self.path):
            self._repo = gitflow.core.GitFlow(self.path.strpath)
            if not self._repo.is_initialized():
                self._repo.init()

    def sync(self):
        """
        Either clone or update, and push all commits.
        """
        if self.repo is None:
            self.clone()
