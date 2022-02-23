from __future__ import absolute_import, print_function

import re
import os
import py
import git
import six
import socket
from termcolor import colored as colored_orig
import subprocess

_COLORS = not os.environ.get("ZENDEV_COLORS", "").lower() in (
    "0",
    "false",
    "no",
    "none",
)


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


here = py.path.local(__file__).dirpath().join

#
# def is_manifest(path):
#     """
#     Path is a filesystem path potentially representing a JSON manifest.
#     """
#     path = py.path.local(path)
#     if not path.check(file=True):
#         return False
#     try:
#         with path.open() as f:
#             json.load(f)
#     except ValueError:
#         return False
#     return True
#
#
# class Reprinter(object):
#     def __init__(self):
#         self.text = ''
#
#     def moveup(self, lines):
#         for _ in range(lines):
#             sys.stdout.write("\x1b[A")
#
#     def clear(self):
#         count = self.text.count('\n')
#         self.moveup(count)
#         for _ in range(count):
#             sys.stdout.write("\x1b[K\n")
#         self.moveup(count)
#
#     def reprint(self, text):
#         self.clear()
#         sys.stdout.write(text)
#         self.text = text


def memoize(f):
    class memodict(dict):
        def __missing__(self, key):
            ret = self[key] = f(key)
            return ret

    return memodict().__getitem__


def colored(s, color=None):
    return s if not _COLORS else colored_orig(s, color)


#
#
# _isurl = re.compile(r'^https?://').search
# def resolve(path):
#     """
#     If path is a URL, download the file somewhere and return the file path.
#     """
#     if isinstance(path, basestring) and _isurl(path):
#         url = path
#         local_filename = \
#             url.split('/')[-1].split('?')[0].split('#')[0] or 'download'
#         path = py.path.local.mkdtemp().join(local_filename).strpath
#         r = requests.get(url, stream=True)
#         with open(path, 'wb') as f:
#             for chunk in r.iter_content(chunk_size=1024):
#                 if chunk:
#                     f.write(chunk)
#                     f.flush()
#     return path
#
# here = py.path.local(__file__).dirpath().join
#
#
# def add_repo_narg(parser):
#     parser.add_argument('repos', nargs='*', help='List of repositories')


def repofilter(repos=(), field_fn=lambda x: x.name):
    """
    Create a function that will return only those repos specified, or all if
    nothing was specified.
    """
    if isinstance(repos, six.string_types):
        repos = (repos,)

    patterns = [re.compile(r, re.I) for r in repos]

    def filter_(repo):
        if repos:
            return any(p.search(field_fn(repo)) for p in patterns)
        return True

    return filter_


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.2.3.4", 9))
        return s.getsockname()[0]
    except socket.error:
        return None
    finally:
        del s


def get_tmux_name():
    """Return the name of the current tmux window."""
    if os.environ.get("TMUX"):
        return subprocess.check_output(
            "tmux list-panes -F '#W' 2>/dev/null",
            shell=True,
        ).strip().decode("utf8")


def rename_tmux_window(name=None):
    """
    Inside tmux renames current window.
    """
    if os.environ.get("TMUX") and name:
        subprocess.call(
            "tmux rename-window {} >/dev/null 2>&1".format(name), shell=True
        )
