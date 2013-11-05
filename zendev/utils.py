import py
import git
import json


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

