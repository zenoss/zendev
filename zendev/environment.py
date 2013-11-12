import sys
import py
import time
import os
import itertools
from multiprocessing import Queue, Pool
from Queue import Empty
from tabulate import tabulate

from .log import info, error
from .config import get_config
from .manifest import Manifest
from .repo import Repository
from .box import VagrantManager
from .utils import Reprinter, colored
from .utils import is_git_repo
from .progress import GitProgressBar, SimpleGitProgressBar
from git.remote import RemoteProgress



CONFIG_DIR = '.zendev'
STATUS_HEADERS = ["Path", "Branch", "Staged", "Unstaged", "Untracked"]


class NotInitialized(Exception): pass


class MultiprocessingProgress(RemoteProgress):

    QUEUE = Queue()

    def __init__(self, path):
        self.path = path
        super(MultiprocessingProgress, self).__init__()

    def update(self, *args, **kwargs):
        self.QUEUE.put((args, kwargs, self.path))


def doit(repo, fname):
    repo.progress = MultiprocessingProgress(repo.path)
    getattr(repo, fname)()


def init_config_dir():
    """
    Create a config directory in PWD.

    :returns the config dir
    """
    cfgdir = py.path.local().ensure(CONFIG_DIR, dir=True)
    manifest = Manifest(cfgdir.join('manifest'))
    manifest.save()
    return cfgdir


def get_config_dir(path=None):
    if path is None:
        paths = py.path.local().parts(reverse=True)
    else:
        paths = [py.path.local(path)]
    for path in paths:
       cfgdir = path.join(CONFIG_DIR)
       if cfgdir.check():
           break
    else:
        raise NotInitialized()
    return cfgdir


class ZenDevEnvironment(object):

    _root = None
    _config = None
    _manifest = None

    def __init__(self, name=None, path=None):
        if path:
            path = py.path.local(path)
        elif name:
            path = py.path.local(get_config().environments.get(name).get('path'))
        else:
            path = py.path.local()
        cfg_dir = get_config_dir(path)
        self.name = name
        self._config = cfg_dir
        self._root = py.path.local(cfg_dir.dirname)
        self._srcroot = self._root.ensure('src', dir=True)
        self._vroot = self._root.ensure('vagrant', dir=True)
        self._manifest = Manifest(self._config.join('manifest'))
        self._vagrant = VagrantManager(self)

    @property
    def srcroot(self):
        return self._srcroot

    @property
    def root(self):
        return self._root

    @property
    def vagrantroot(self):
        return self._vroot

    @property
    def manifest(self):
        """
        Get the manifest associated with this environment.
        """
        return self._manifest

    @property
    def vagrant(self):
        """
        Get the Vagrant manager.
        """
        return self._vagrant

    def _repos(self):
        for path, info in self.manifest.repos().iteritems():
            fullpath = self._srcroot.join(path)
            repo = Repository(path, fullpath, **info)
            yield repo

    def repos(self, filter_=None, key=None):
        """
        Get Repository objects for all repos in the system.
        """
        return sorted(itertools.ifilter(filter_, self._repos()), 
                key=key or (lambda r:r.name.count('/')))

    def remove(self, filter_=None):
        """
        Remove repositories from the manifest and filesystem. In this case, if
        there are no repos passed in, fail.
        """
        repoinfo = self.manifest.repos()
        for repo in self.repos(filter_):
            repoinfo.pop(repo.name)
            try:
                repo.path.remove()
            except:
                info("Unable to remove path %s." % repo.path.strpath)
        self.manifest.save()

    def freeze(self):
        """
        Return a JSON representation of the repositories.
        """
        return self.manifest.freeze()

    def ensure_build(self):
        builddir = self._root.join('build')
        if builddir.check() and not is_git_repo(builddir):
            error("%s exists but isn't a git repository. Not sure "
                    "what to do." % builddir)
        else:
            if not builddir.check(dir=True):
                repo = Repository('build', builddir, 
                        repo='zenoss/platform-build',
                        ref='develop')
                info("Checking out build repository")
                repo.progress = SimpleGitProgressBar('build')
                repo.clone()
                print
            else:
                info("Build repository exists")

    def initialize(self):
        # Clone build directory
        self.ensure_build()

    def clone(self):
        info("Cloning repositories")
        self.foreach('clone', lambda r:not r.repo)
        info("All repositories are cloned!")

    def fetch(self):
        info("Checking for remote changes")
        self.foreach('fetch', silent=True)

    def sync(self, filter_=None):
        self.clone()
        self.fetch()
        for repo in self.repos(filter_):
            repo.merge_from_remote()
        info("Remote changes have been merged")
        for repo in self.repos(filter_):
            repo.push()
        info("Up to date!")

    def use(self):
        get_config().current = self.name

    def status(self, filter_=None):
        table = []
        for repo in self.repos(filter_):
            staged, unstaged, untracked = repo.changes
            color = 'green' if staged else 'blue' if unstaged else None
            table.append([colored(x, color) for x in [
                repo.name,
                repo.branch,
                '*' if staged else '',
                '*' if unstaged else '',
                '*' if untracked else ''
            ]])
        print tabulate(table, headers=STATUS_HEADERS)

    def foreach(self, fname, filter_=None, silent=False):
        """
        Execute a method on all repositories in subprocesses.
        """
        repos = list(self.repos(filter_))

        if not repos:
            return

        _pool = Pool(len(repos))

        results = {}
        bars = {}
        barlist = []

        justification = max(len(p.name) for p in repos)

        for repo in repos:
            name = repo.name
            path = repo.path
            result = _pool.apply_async(doit, (repo, fname))
            results[path] = result
            bars[path] = GitProgressBar(name, justification)
            barlist.append(bars[path])

        _pool.close()

        barlist.sort(key=lambda bar:bar.name.count('/'))

        def ready():
            done = []
            for path, result in results.iteritems():
                if result.ready():
                    bars[path].done()
                    done.append(path)
            for d in done:
                del results[d]
            return not results

        printer = Reprinter()
        start = time.time()

        REFRESHINTERVAL = 0.1

        def printscreen():
            text = ''
            for bar in barlist:
                text += bar.get() + '\n'
            if not silent:
                printer.reprint(text)

        updated = True

        printscreen()

        while True:
            text = ''
            try:
                qresult = MultiprocessingProgress.QUEUE.get(timeout=0.1)
                (op_code, cur_count, max_count, msg), _, path = qresult
                bars[path].update(op_code, cur_count, max_count)
                updated = True
            except Empty:
                if ready():
                    break
                continue

            now = time.time()
            if now - start > REFRESHINTERVAL:
                printscreen()
                start = now

        if updated:
            printscreen()
