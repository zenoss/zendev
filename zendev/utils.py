import re
import sys
import os
import py
import git
import json

import requests
from termcolor import colored as colored_orig

_COLORS = not os.environ.get("ZENDEV_COLORS", '').lower() in ('0', 'false', 'no', 'none')


def is_git_repo(path):
    """
    Path is a filesystem path or a remote URI.
    """
    if not py.path.local(path).check(dir=True):
        return False
    try:
        git.Repo(str(path))
        return True
    except git.InvalidGitRepositoryError:
        return False


def is_manifest(path):
    """
    Path is a filesystem path potentially representing a JSON manifest.
    """
    path = py.path.local(path)
    if not path.check(file=True):
        return False
    try:
        with path.open() as f:
            json.load(f)
    except ValueError:
        return False
    return True


class Reprinter(object):
    def __init__(self):
        self.text = ''

    def moveup(self, lines):
        for _ in range(lines):
            sys.stdout.write("\x1b[A")

    def clear(self):
        count = self.text.count('\n')
        self.moveup(count)
        for _ in range(count):
            sys.stdout.write("\x1b[K\n")
        self.moveup(count)

    def reprint(self, text):
        self.clear()
        sys.stdout.write(text)
        self.text = text


def memoize(f):
    class memodict(dict):
        def __missing__(self, key):
            ret = self[key] = f(key)
            return ret 
    return memodict().__getitem__


def colored(s, color=None):
    return s if not _COLORS else colored_orig(s, color)


_isurl = re.compile(r'^https?://').search
def resolve(path):
    """
    If path is a URL, download the file somewhere and return the file path.
    """
    if isinstance(path, basestring) and _isurl(path):
        url = path
        local_filename = url.split('/')[-1].split('?')[0].split('#')[0] or 'download'
        path = py.path.local.mkdtemp().join(local_filename).strpath
        r = requests.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
    return path

here = py.path.local(__file__).dirpath().join


def add_repo_narg(parser):
    parser.add_argument('repos', nargs='*', help='List of repositories')


def repofilter(repos=()):
    """
    Create a function that will return only those repos specified, or all if
    nothing was specified.
    """
    patterns = [re.compile(r, re.I) for r in repos]

    def filter_(repo):
        if repos:
            return any(p.search(repo.name) for p in patterns)
        return True

    return filter_


