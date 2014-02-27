import json
import py

from .utils import resolve


class Manifest(object):
    """
    A repository manifest.
    """
    _path = None
    _data = None

    def __init__(self, path):
        self._path = py.path.local(path)
        if self._path.check():
            with self._path.open() as f:
                self._data = json.load(f)
        else:
            self._data = {
                'repos':{}
            }

    def repos(self):
        return self._data.setdefault('repos', {})

    def save(self):
        self._path.write(json.dumps(self._data, 
            indent=4))

    def freeze(self):
        return json.dumps(self._data, indent=4)

    def merge(self, manifest):
        assert isinstance(manifest, Manifest)
        self.repos().update(manifest.repos())


def create_manifest(manifest):
    """
    Turn paths/urls to one or more manifests into a single Manifest instance.
    """
    if not hasattr(manifest, '__iter__'):
        manifest = (py.path.local(manifest).strpath,)
    m = None
    for path in manifest:
        m2 = Manifest(resolve(path))
        if isinstance(m, Manifest):
            m.merge(m2)
        else:
            m = m2
    return m
