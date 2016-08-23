import os

import py
import subprocess

from .log import info, error
from .config import get_config
from .utils import is_git_repo, here


CONFIG_DIR = '.zendev'
STATUS_HEADERS = ["Path", "Branch", "Staged", "Unstaged", "Untracked"]


class NotInitialized(Exception): pass


def call_repo_member(repo, fname):
    getattr(repo, fname)()

def init_config_dir():
    """
    Create a config directory in PWD.

    :returns the config dir
    """
    cfgdir = py.path.local().ensure(CONFIG_DIR, dir=True)
    return cfgdir

def get_config_dir(path=None):
    if path is None:
        paths = py.path.local().parts(reverse=True)
    else:
        paths = [py.path.local(path)]
    for path in paths:
       cfgdir = path.join(CONFIG_DIR, abs=1)
       if cfgdir.check():
           break
    else:
        raise NotInitialized()
    return cfgdir


class ZenDevEnvironment(object):

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
        self._gopath = self._srcroot
        self._zenhome = self._root.ensure('zenhome', dir=True)
        self._var_zenoss = self._root.ensure('var_zenoss', dir=True)
        self._bash = open(os.environ.get('ZDCTLCHANNEL', os.devnull), 'w')

    def envvars(self):
        origpath = os.environ.get('PATH')
        previousMod = os.environ.get('ZD_PATH_MOD', "")
        if len(previousMod) > 0:
            origpath = origpath.replace(previousMod, "")
        newMod = "%s/bin:%s/bin:" % (self._gopath, self._zenhome)
        return {
            "ZENHOME": self._zenhome.strpath,
            "SRCROOT": self._srcroot.strpath,
            "GOPATH": self._gopath.strpath,
            "GOBIN": self._gopath.strpath + "/bin",
            "ZD_PATH_MOD": newMod,
            "PATH":"%s%s" % (newMod, origpath)
        }

    def _export_env(self):
        for k, v in self.envvars().iteritems():
            self.bash('export %s="%s"' % (k, v))

    @property
    def srcroot(self):
        return self._srcroot

    @property
    def configroot(self):
        return self._config

    @property
    def root(self):
        return self._root

    @property
    def var_zenoss(self):
        return self._var_zenoss

    @property
    def zenhome(self):
        return self._zenhome

    @property
    def zendev(self):
        return here("..")

    def bash(self, command):
        print >>self._bash, command

    def _ensure_product_assembly(self):
        repodir = py.path.local(os.path.join('github.com','zenoss', 'product-assembly'))
        if repodir.check() and not is_git_repo(repodir):
            error("%s exists but isn't a git repository. Not sure "
                  "what to do." % repodir)
        else:
            if not repodir.check(dir=True):
                info("Checking out product-assembly repository")
                github_zenoss = self.srcroot.ensure('github.com','zenoss', dir=True)
                github_zenoss.chdir()
                subprocess.check_call(['git', 'clone', '--progress', 'https://github.com/zenoss/product-assembly.git'])

    def initialize(self):
        # Clone product-assembly directory
        self._ensure_product_assembly()

    def use(self, switch_dir=True):
        get_config().current = self.name
        if switch_dir:
            self.bash('cd "%s"' % self.root.strpath)
        self._export_env()


