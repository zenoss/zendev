import sys
import py
import time
from multiprocessing import Queue, Pool
from Queue import Empty

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



def doit(path, info, fname):
    repo = Repository(path, **info)
    repo.progress = MultiprocessingProgress(path)
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

    def repos(self):
        """
        Get Repository objects for all repos in the system.
        """
        for path, info in self.manifest.repos().iteritems():
            path = self._srcroot.join(path)
            yield Repository(path, **info)

    def freeze(self):
        """
        Return a JSON representation of the repositories.
        """
        return self.manifest.freeze()

    def sync(self):
        self.foreach('sync')

    def foreach(self, fname):

        repos = self.manifest.repos().items()

        _pool = Pool()

        results = {}
        bars = {}
        barlist = []

        justification = max(len(p) for p in self.manifest.repos())

        for path, info in repos:
            name = path
            path = self._srcroot.join(path).strpath
            result = _pool.apply_async(doit, (path, info, fname))
            results[path] = result
            bars[path] = GitProgressBar(name, justification)
            barlist.append(bars[path])

        _pool.close()

        def ready():
            return all(x.ready() for x in results.itervalues())

        printer = Reprinter()
        start = time.time()

        REFRESHINTERVAL = 0.1

        def printscreen():
            text = ''
            for bar in barlist:
                text += bar.get() + '\n'
            printer.reprint(text)

        updated = False

        while True:
            text = ''
            try:
                qresult = MultiprocessingProgress.QUEUE.get(timeout=0.5)
                (op_code, cur_count, max_count, message), _, path = qresult
                bars[path].update(op_code, cur_count, max_count, message)
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
