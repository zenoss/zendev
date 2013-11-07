import sys
import py
import time
import itertools
from multiprocessing import Queue, Pool
from Queue import Empty
from termcolor import colored

from .manifest import Manifest
from .repo import Repository
from .utils import Reprinter
from .progress import GitProgressBar
from git.remote import RemoteProgress



CONFIG_DIR = '.zendev'


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


def get_config_dir():
    for path in py.path.local().parts(reverse=True):
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

    def __init__(self):
        cfg_dir = get_config_dir()
        self._config = cfg_dir
        self._root = py.path.local(cfg_dir.dirname)
        self._srcroot = self._root.ensure('src', dir=True)
        self._manifest = Manifest(self._config.join('manifest'))

    @property
    def manifest(self):
        """
        Get the manifest associated with this environment.
        """
        return self._manifest

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

    def freeze(self):
        """
        Return a JSON representation of the repositories.
        """
        return self.manifest.freeze()

    def message(self, msg):
        print colored('==>', 'blue'), colored(msg, 'white')

    def clone(self):
        self.message("Cloning repositories...")
        self.foreach('clone', lambda r:not r.repo)
        self.message("All repositories are cloned!")

    def fetch(self):
        self.message("Checking for remote changes...")
        self.foreach('fetch', silent=True)

    def sync(self):
        self.clone()
        self.fetch()
        for repo in self.repos():
            repo.merge_from_remote()
        self.message("All remote changes have been merged.")
        for repo in self.repos():
            repo.push()
        self.message("Up to date!")

    def status(self, filter_=None):
        for repo in self.repos(filter_):
            pass

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
                (op_code, cur_count, max_count, message), _, path = qresult
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
