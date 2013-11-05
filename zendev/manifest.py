
class Manifest(object):
    """
    A repository manifest.
    """
    _path = None
    _data = None

    def __init__(self, data):
        self._data = data

    @staticmethod
    def load(path):
        with open(path) as f:
            json.load(f)
        mf = Manifest()
        mf._path = path

    def repos(self):
        repos = self._data.get('repos', {})
        for path, info in repos.iteritems():
            yield path, info