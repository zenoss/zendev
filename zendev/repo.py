import re
import sys

import gitflow.core
import py

from git.exc import GitCommandError

from .utils import is_git_repo, memoize


is_github = re.compile(r"^[^\/\s@]+\/[^\/\s]+$").match


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
            return "git@github.com:" + url
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
            kwargs["depth"] = 1
        if self.ref:
            kwargs["branch"] = self.ref
        if self.path.check():
            raise Exception(
                "Something already exists at %s. "
                "Remove it first." % self.path
            )
        else:
            self.path.dirpath().ensure(dir=True)
            try:
                gitrepo = gitflow.core.Repo.clone_from(
                    self.url, str(self.path), progress=self.progress, **kwargs
                )
            except GitCommandError:
                # Can't clone a hash, so clone the entire repo and check out
                # the ref
                gitrepo = gitflow.core.Repo.clone_from(
                    self.url, str(self.path), progress=self.progress
                )
                gitrepo.git.checkout(self.ref)
            self._repo = gitflow.core.GitFlow(gitrepo)
            if not shallow:
                self.initialize()

    def merge_from_remote(self):
        try:
            active_branch = self.repo.repo.active_branch
        except TypeError:
            # We're detached
            return
        local_name = active_branch.name
        tracking = active_branch.tracking_branch()
        remote_name = tracking.name if tracking else local_name

        if self.repo.is_merged_into(remote_name, local_name):
            # Nothing to do
            return
        print(
            "Changes found in %s:%s! Rebasing %s..."
            % (self.name, remote_name, local_name)
        )
        self.repo.git.rebase(remote_name, output_stream=sys.stderr)

    def fetch(self):
        self.repo.git.fetch(all=True)

    def initialize(self):
        if not self._repo and is_git_repo(self.path):
            self._repo = gitflow.core.GitFlow(self.path.strpath)
        if self._repo and not self._repo.is_initialized():
            py.io.StdCaptureFD.call(self._repo.init)
        if self._repo and not self._repo.get("include.path", ""):
            self._repo.set("include.path", "../gitflow-branch-config")
