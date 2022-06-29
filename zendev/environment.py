from __future__ import absolute_import, print_function

import json
import os
import py
import subprocess
import sys

try:
    # Python 2
    from future_builtins import filter
except ImportError:
    # Python 3
    pass

from .log import info, error
from .config import get_config
from .repo import Repository
from .utils import is_git_repo, here

CONFIG_DIR = ".zendev"
STATUS_HEADERS = ["Path", "Branch", "Staged", "Unstaged", "Untracked"]


class NotInitialized(Exception):
    pass


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
            path = py.path.local(
                get_config().environments.get(name).get("path")
            )
        else:
            path = py.path.local()
        cfg_dir = get_config_dir(path)
        self.name = name
        self._config = cfg_dir
        self._repos_file = self._config.join(".repos.json")
        self._root = py.path.local(cfg_dir.dirname)
        self._srcroot = self._root.ensure("src", dir=True)
        self.gopath = self._root
        self.servicedhome = self._root.ensure("opt_serviced", dir=True)
        self.servicedsrc = self._srcroot.join(
            "github.com", "control-center", "serviced"
        )
        self._prodbinsrc = self._srcroot.join(
            "github.com", "zenoss", "zenoss-prodbin"
        )
        self._zenhome = self._root.ensure("zenhome", dir=True)
        self._var_zenoss = self._root.ensure("var_zenoss", dir=True)
        self._productAssembly = self._srcroot.join(
            "github.com", "zenoss", "product-assembly"
        )
        self._bash = open(os.environ.get("ZDCTLCHANNEL", os.devnull), "w")
        self._export_env()

    def envvars(self):
        origpath = os.environ.get("PATH")
        previousMod = os.environ.get("ZD_PATH_MOD", "")
        if len(previousMod) > 0:
            origpath = origpath.replace(previousMod, "")
        newMod = "%s/bin:" % (self.gopath)
        return {
            "ZENHOME": self._zenhome.strpath,
            "SRCROOT": self._srcroot.strpath,
            "JIGROOT": self._srcroot.strpath,
            "GOPATH": self.gopath.strpath,
            "ZD_PATH_MOD": newMod,
            "SERVICED_HOME": self.servicedhome.strpath,
            "PATH": "%s%s" % (newMod, origpath),
        }

    def _export_env(self):
        envvars = self.envvars()
        for k, v in envvars.items():
            self.bash('export %s="%s"' % (k, v))
        os.environ.update(envvars)

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

    @property
    def productAssembly(self):
        return self._productAssembly

    @property
    def prodbinsrc(self):
        return self._prodbinsrc

    def bash(self, command):
        print(command, file=self._bash)

    def _ensure_product_assembly(self):
        if self._productAssembly.check() and not is_git_repo(
            self._productAssembly
        ):
            error(
                "%s exists but isn't a git repository. Not sure "
                "what to do." % self._productAssembly.strpath
            )
            sys.exit(1)
        else:
            repo = Repository(
                self._productAssembly.strpath,
                self._productAssembly.strpath,
                "zenoss/product-assembly",
            )
            if not self._productAssembly.check(dir=True):
                info("Cloning product-assembly repository")
                github_zenoss = self.srcroot.ensure(
                    "github.com", "zenoss", dir=True
                )
                github_zenoss.chdir()
                repo.clone()
                subprocess.check_call(["jig", "add", "product-assembly"])
            return repo

    def _ensure_prodbin(self):
        if self._prodbinsrc.check() and not is_git_repo(self._prodbinsrc):
            error(
                "%s exists but isn't a git repository. Not sure "
                "what to do." % self._prodbinsrc.strpath
            )
            sys.exit(1)
        else:
            repo = Repository(
                self._prodbinsrc.strpath,
                self._prodbinsrc.strpath,
                "zenoss/zenoss-prodbin",
            )
            if not self._prodbinsrc.check(dir=True):
                info("Cloning zenoss-prodbin repository")
                github_zenoss = self.srcroot.ensure(
                    "github.com", "zenoss", dir=True
                )
                github_zenoss.chdir()
                repo.clone()
                subprocess.check_call(["jig", "add", "zenoss-prodbin"])
            return repo

    def _initializeJig(self):
        self._srcroot.chdir()
        if not self._srcroot.join(".jig").check():
            subprocess.check_call(["jig", "init"])

    def initialize(self, shallow=False, tag="develop"):
        # Clone product-assembly directory
        self._initializeJig()
        # Initialize the env with the specified tag
        self.restore(tag, shallow=shallow)

    def generateRepoJSON(self):
        repos_sh = self._productAssembly.join("repos.sh")
        if not repos_sh.check():
            error("%s does not exist" % repos_sh.strpath)
            sys.exit(1)
        else:
            # run from _config dir so that repos.json is created there
            self._config.chdir()
            subprocess.check_call([repos_sh.strpath])
            if not self._repos_file.check():
                error("%s does not exist" % self._repos_file.strpath)
                sys.exit(1)
            return self._repos_file

    def generateZVersions(self):
        self._ensure_prodbin()

        print("cd %s" % self._prodbinsrc.strpath)
        self._prodbinsrc.chdir()

        cmdArgs = ["make", "generate-zversion"]
        print(" ".join(cmdArgs))
        subprocess.check_call(cmdArgs)

    def use(self, switch_dir=True):
        get_config().current = self.name
        if switch_dir:
            self.bash('cd "%s"' % self.root.strpath)

    def restore(self, ref, shallow=False):
        repo = self._ensure_product_assembly()
        info("Checking out '%s' for product-assembly ..." % ref)
        repo.checkout(ref)
        repo.fetch()
        repo.merge_from_remote()
        info("Generating list of github repos and versions ...")
        repos_json = self.generateRepoJSON()

        info("Checking out github repos defined by %s" % repos_json.strpath)
        self._srcroot.chdir()
        args = ["jig", "restore"]
        if shallow:
            args.append("--shallow")
        args += [repos_json.strpath]
        subprocess.check_call(args)
        subprocess.check_call(
            ["jig", "add", "github.com/zenoss/product-assembly"]
        )

    def _repos(self):
        if not self._repos_file.check():
            error("%s does not exist" % self._repos_file.strpath)
            sys.exit(1)

        with self._repos_file.open() as f:
            repos_list = json.load(f)
        for item in repos_list:
            name = str(item["repo"])
            if name.startswith("git@"):
                name = name[len("git@"):]
                name = name.replace(":", "/")
            elif name.startswith("https://"):
                name = name[len("https://"):]
            if name.endswith(".git"):
                name = name[0: len(name) - len(".git")]
            repopath = self._srcroot.join(name)
            repo = Repository(repopath.strpath, repopath.strpath, name)
            yield repo

    def repos(self, filter_=None, key=None):
        """
        Get Repository objects for all repos in the system.
        """
        return sorted(
            filter(filter_, self._repos()),
            key=key or (lambda r: r.name.count("/")),
        )
