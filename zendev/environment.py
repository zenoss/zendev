import sys
import py

from .manifest import Manifest
from .repo import Repository
from .progress import MultiGit
from git.remote import RemoteProgress



CONFIG_DIR = '.zendev'


class NotInitialized(Exception): pass


class MultiprocessingProgress(RemoteProgress):
    def __init__(self, queue):
        self.queue = queue
        super(MultiprocessingProgress, self).__init__()

    def update(self, *args, **kwargs):
        print args, kwargs
        self.queue.put((args, kwargs))


QUEUES = {}

def doit(path, info, fname):
    repo = Repository(path, **info)
    repo.progress = MultiprocessingProgress(QUEUES[path])
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
        from multiprocessing import Queue, Pool
        queues = QUEUES


        for path, info in self.manifest.repos().iteritems():
            q = Queue()
            path = self._srcroot.join(path).strpath
            queues[path] = q

        _pool = Pool()

        results = []

        for path, info in self.manifest.repos().iteritems():
            path = self._srcroot.join(path).strpath
            result = _pool.apply_async(doit, (path, info, fname))
            results.append(result)

        _pool.close()

        def ready():
            return all(x.ready() for x in results)

        while not ready():
            for queue in queues.values():
                try:
                    print queue.get(timeout=0.01)
                except Exception:
                    pass


