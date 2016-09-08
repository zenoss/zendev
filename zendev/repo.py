import re
import sys

from git.exc import GitCommandError
from termcolor import colored
import gitflow.core
import py
import time
import json

from .log import error, info
from .utils import is_git_repo, memoize


is_github = re.compile('^[^\/\s@]+\/[^\/\s]+$').match


class Repository(object):
    """
    A repository.
    """
    def __init__(self, localpath, path, repo, name="", ref="develop"):
        self.name = name or localpath
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
        try:
            return self.repo.repo.active_branch.name
        except TypeError:
            head = self.repo.repo.head
            sha, target = head._get_ref_info(head.repo, head.path)
            return sha

    @property
    @memoize
    def repo(self):
        self.initialize()
        return self._repo

    def checkout(self, ref):
        if ref != self.branch:
            self.repo.repo.git.checkout(ref)

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
            try:
                gitrepo = gitflow.core.Repo.clone_from(
                    self.url,
                    str(self.path),
                    progress=self.progress,
                    **kwargs)
            except GitCommandError:
                # Can't clone a hash, so clone the entire repo and check out
                # the ref
                gitrepo = gitflow.core.Repo.clone_from(
                    self.url,
                    str(self.path),
                    progress=self.progress)
                gitrepo.git.checkout(self.ref)
            self._repo = gitflow.core.GitFlow(gitrepo)
            if not shallow:
                self.initialize()

    def shallow_clone(self):
        return self.clone(shallow=True)

    def initialize(self):
        if not self._repo and is_git_repo(self.path):
            self._repo = gitflow.core.GitFlow(self.path.strpath)
        if self._repo and not self._repo.is_initialized():
            py.io.StdCaptureFD.call(self._repo.init)
