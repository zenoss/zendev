import json
import py


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

    def repos(self, raw=True):
        return self._data.setdefault('repos', {})

    def save(self):
        self._path.write(json.dumps(self._data, 
            indent=4))

    def freeze(self):
        return json.dumps(self._data, indent=4)

    def merge(self, manifest):
        assert isinstance(manifest, Manifest)
        self.repos().update(manifest.repos())
