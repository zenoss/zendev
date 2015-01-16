import sys
import time
import os
import itertools
from multiprocessing import Queue, Pool
from Queue import Empty

import py
from tabulate import tabulate
from git.remote import RemoteProgress

from .log import ask, info, error
from .config import get_config
from .manifest import Manifest, create_manifest
from .repo import Repository
from .cmd.box import VagrantBoxManager
from .cmd.cluster import VagrantClusterManager
from .utils import Reprinter, colored, here
from .utils import is_git_repo
from .progress import GitProgressBar, SimpleGitProgressBar


CONFIG_DIR = '.zendev'
STATUS_HEADERS = ["Path", "Branch", "Staged", "Unstaged", "Untracked"]


class NotInitialized(Exception): pass


class MultiprocessingProgress(RemoteProgress):

    QUEUE = Queue()

    def __init__(self, path):
        self.path = path
        super(MultiprocessingProgress, self).__init__()

    def update(self, *args, **kwargs):
        self.QUEUE.put((args, kwargs, self.path))


def doit(repo, fname):
    repo.progress = MultiprocessingProgress(repo.path)
    try:
        getattr(repo, fname)()
    except Exception as e:
        error(e.message)



def init_config_dir():
    """
    Create a config directory in PWD.

    :returns the config dir
    """
    cfgdir = py.path.local().ensure(CONFIG_DIR, dir=True)
    manifest = Manifest(cfgdir.join('manifest'))
    manifest.save()
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

    _root = None
    _config = None
    _manifest = None
    _buildrepo_name = 'build'

    def __init__(self, name=None, path=None, manifest=None, srcroot=None,
            buildroot=None, zenhome=None, var_zenoss=None):
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
        self._srcroot = (py.path.local(srcroot).ensure(dir=True) if srcroot 
                else self._root.ensure('src', dir=True))
        self._gopath = self._srcroot.ensure('golang', dir=True)
        self._vroot = self._root.join('vagrant')
        self._croot = self._vroot.join('clusters')
        self._zenhome = (py.path.local(zenhome).ensure(dir=True) if zenhome 
                else self._root.ensure('zenhome', dir=True))
        self._var_zenoss = (py.path.local(var_zenoss).ensure(dir=True) if var_zenoss
                else self._root.ensure('var_zenoss', dir=True))
        self._buildroot = (py.path.local(buildroot) if buildroot
                else self._root.join(ZenDevEnvironment._buildrepo_name))
        self._manifestroot = self._root.join('.manifest')
        self._manifest = create_manifest(manifest or self._config.join('manifest'))
        self._add_build_repo(self._manifest, self._srcroot, self._buildroot)
        self._vagrant = VagrantBoxManager(self)
        self._cluster = VagrantClusterManager(self)
        self._bash = open(os.environ.get('ZDCTLCHANNEL', os.devnull), 'w')

    def _add_build_repo(self, manifest, srcroot, buildroot):
        buildrepo_dir = py.path.local(srcroot).bestrelpath(
            py.path.local(buildroot))
        buildrepo_data = {'name': ZenDevEnvironment._buildrepo_name,
                          'repo': 'zenoss/platform-build'}
        manifest.repos().setdefault(buildrepo_dir, buildrepo_data)

    def envvars(self):
        origpath = os.environ.get('ZD_ORIGPATH', os.environ.get('PATH'))
        return {
            "ZENHOME": self._zenhome.strpath,
            "SRCROOT": self._srcroot.strpath,
            "GOPATH": self._gopath.strpath,
            "GOBIN": self._gopath.strpath + "/bin",
            "ZD_ORIGPATH": origpath,
            "PATH":"%s/bin:%s/bin:%s" % (self._gopath, self._zenhome, origpath)
        }

    def _export_env(self):
        for k, v in self.envvars().iteritems():
            self.bash('export %s="%s"' % (k, v))

    @property
    def srcroot(self):
        return self._srcroot

    @property
    def gopath(self):
        return self._gopath

    @property
    def configroot(self):
        return self._config

    @property
    def buildroot(self):
        return self._buildroot

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
    def vagrantroot(self):
        return self._vroot

    @property
    def clusterroot(self):
        return self._croot

    @property
    def manifest(self):
        """
        Get the manifest associated with this environment.
        """
        return self._manifest

    @property
    def vagrant(self):
        """
        Get the Vagrant manager.
        """
        return self._vagrant

    @property
    def cluster(self):
        """
        Get the Vagrant cluster manager.
        """
        return self._cluster

    def bash(self, command):
        print >>self._bash, command

    def _repos(self):
        for path, info in self.manifest.repos().iteritems():
            fullpath = self._srcroot.join(path)
            repo = Repository(path, fullpath, **info)
            yield repo

    def repos(self, filter_=None, key=None):
        """
        Get Repository objects for all repos in the system.
        """
        return sorted(itertools.ifilter(filter_, self._repos()), 
                key=key or (lambda r:r.name.count('/')))

    def remove(self, filter_=None, save=True):
        """
        Remove repositories from the manifest and filesystem. In this case, if
        there are no repos passed in, fail.
        """
        repoinfo = self.manifest.repos()
        for repo in self.repos(filter_):
            repoinfo.pop(repo.name)
            try:
                repo.path.remove()
            except:
                info("Unable to remove path %s." % repo.path.strpath)
        if save:
            self.manifest.save()

    def _update_manifest(self, hashes=False):
        """
        Update the manifest's branches with those on the filesystem.
        """
        for repo in self.repos():
            name = repo.name
            repodict = None
            try:
                repodict = self.manifest.repos()[name]
            except KeyError:
                for r, d in self.manifest.repos().iteritems():
                    if d.get('name') == name:
                        repodict = d
            if repodict is not None:
                repodict['ref'] = repo.hash if hashes else repo.branch
        self.manifest.save()

    def freeze(self, hashes=False):
        """
        Return a JSON representation of the repositories.
        """
        try:
            self._update_manifest(hashes)
            return self.manifest.freeze()
        finally:
            if hashes:
                # Undo the hash saving
                self._update_manifest()

    def ensure_manifestrepo(self):
        repo = Repository(os.path.join('..', '.manifest'), self._manifestroot,
                          'zenoss/manifest', ref="master")
        repodir = repo.path
        if repodir.check() and not is_git_repo(repodir):
            error("%s exists but isn't a git repository. Not sure "
                  "what to do." % repodir)
        else:
            if not repodir.check(dir=True):
                info("Checking out manifest repository")
                if sys.stdout.isatty():
                    repo.progress = SimpleGitProgressBar(repo.name)
                repo.clone()
                print
        return repo

    def refresh_manifests(self):
        repo = self.ensure_manifestrepo()
        repo.checkout('master')
        repo.repo.git.fetch('--tags')

    def restore(self, ref, shallow=False):
        self.refresh_manifests()
        repo = self.ensure_manifestrepo()
        repo.checkout(ref)
        repo.fetch()
        repo.merge_from_remote()
        self.manifest.merge(create_manifest(
            self._manifestroot.join('manifest.json')))
        self.manifest.save()
        self.sync(force_branch=True, shallow=shallow)
        info("Manifest '%s' has been restored" % ref)

    def get_manifest(self, ref):
        self.refresh_manifests()
        repo = self.ensure_manifestrepo()
        repo.checkout(ref)
        repo.fetch()
        repo.merge_from_remote()
        return create_manifest(self._manifestroot.join('manifest.json'))

    def list_tags(self):
        repo = self.ensure_manifestrepo()
        return repo.tag_names

    def tag(self, name, strict=False, force=False, from_ref=None):
        self.refresh_manifests()
        if name in self.list_tags() and not force:
            error("Tag %s already exists. Use -f/--force to override it." % name)
            return
        repo = self.ensure_manifestrepo()
        repo.checkout('master')
        git = repo.repo.git
        git.reset('--hard')

        if from_ref is not None:
            #restore gets manifest from ref and updates all repos to refs in the manifest
            self.restore(from_ref)

        with open(self._manifestroot.join('manifest.json').strpath, 'w') as f:
            f.write(self.freeze(strict))
        git.commit('-am', 'Saving manifest %s' % name)
        if name in self.list_tags():
            git.tag('-d', name)
        repo.repo.repo.create_tag(name, force=force)
        if force:
            git.push('origin', '-f', '--tags')
        else:
            git.push('origin', '--tags')
        git.reset('--hard', 'HEAD~1')


    def tag_delete(self, name):
        repo = self.ensure_manifestrepo()
        repo.checkout('master')
        repo.repo.git.tag('-d', name)
        repo.repo.git.push('origin', ':%s' % name)

    def ensure_build(self):
        repo = self.repos(lambda x: x.name == ZenDevEnvironment._buildrepo_name)[0]
        builddir = repo.path
        if builddir.check() and not is_git_repo(builddir):
            error("%s exists but isn't a git repository. Not sure "
                  "what to do." % builddir)
        else:
            if not builddir.check(dir=True):
                info("Checking out build repository")
                if sys.stdout.isatty():
                    repo.progress = SimpleGitProgressBar(repo.name)
                repo.clone()
                print
            else:
                info("Build repository exists")

    def initialize(self):
        # Clone manifest directory
        self.ensure_manifestrepo()
        # Clone build directory
        self.ensure_build()

    def clone(self, shallow=False):
        cmd = 'shallow_clone' if shallow else 'clone'
        info("Cloning repositories")
        self.foreach(cmd, lambda r: not r.repo, silent=not sys.stdout.isatty())
        info("All repositories are cloned!")

    def fetch(self):
        info("Checking for remote changes")
        self.foreach('fetch', silent=True)

    def sync(self, filter_=None, force_branch=False, shallow=False):
        self.clone(shallow=shallow)
        self.fetch()
        for repo in self.repos(filter_):
            if force_branch:
                info("Syncing %s" % repo.name)
                repo.checkout(repo.ref)
            repo.merge_from_remote()
        info("Remote changes have been merged")
        for repo in self.repos(filter_):
            repo.push()
        info("Up to date!")

    def use(self):
        get_config().current = self.name
        self.bash('cd "%s"' % self.root.strpath)
        self._export_env()

    def status(self, filter_=None):
        table = []
        for repo in self.repos(filter_):
            if repo.path.check():
                staged, unstaged, untracked = repo.changes
                color = 'green' if staged else 'blue' if unstaged else None
                table.append([colored(x, color) for x in [
                    repo.name,
                    repo.branch,
                    '*' if staged else '',
                    '*' if unstaged else '',
                    '*' if untracked else ''
                ]])
            else:
                table.append([colored(x, 'red') for x in [
                    repo.name,
                    'not synced'
                ]])
        print tabulate(table, headers=STATUS_HEADERS)

    def feature_filter(self, name, filter_):
        fname = "feature/%s" % name
        ofname = "origin/feature/%s" % name
        feature_filter = lambda r: fname in r.local_branches or ofname in r.remote_branches
        if filter_ is None:
          return feature_filter
        else:
          return lambda r : filter_(r) and feature_filter(r)


    def start_feature(self, name, filter_=None):
        info("Starting feature: %s" % name)
        repos = self.repos(filter_)
        repo_names = [r.name for r in repos]
        response = ask("Start feature in these repositories?\n  " + "\n  ".join( repo_names), "(y/n)")
        response = response.lower().strip()

        if not response in ('n','no', 'y', 'yes'):
            error( "illegal response: %s" % response)
            return

        if response in ('n','no'):
            return

        for r in repos:
            info( " Starting feature for repo: %s" % r.name)
            r.create_feature( name)

    def list_feature(self, name):
        info("Repositores with feature: %s" % name)
        fname = "feature/%s" % name
        ofname = "origin/feature/%s" % name
        for r in self.repos(): 
            local = fname in r.local_branches
            remote = ofname in r.remote_branches
            if local and remote:
                info( " %s - local and remote" % r.name)
            elif not local and remote:
                info( " %s - remote" % r.name)
            elif local and not remote:
                info( " %s - local" % r.name)

    def pull_feature(self, name, filter_=None):
        info("Creating pull requests for feature: %s" % name)
        fname = "feature/%s" % name
        ofname = "origin/feature/%s" % name
        filter_ = self.feature_filter(name, filter_)
        repos = self.repos(filter_)

        if len( repos) == 0:
          error("No repos found with feature: %s" % name)
          return

        repo_names = [r.name for r in repos]
        response = ask("Pull request for feature in these repositories?\n  " + "\n  ".join( repo_names), "(y/n)")
        response = response.lower().strip()

        if not response in ('n','no', 'y', 'yes'):
          error( "illegal response: %s" % response)
          return

        if response in ('n','no'):
          return

        for r in repos:
          r.create_pull_request(name)

    def finish_feature(self, name, filter_=None):
        info("Finish feature: %s" % name)
        filter_ = self.feature_filter(name, filter_)
        repos = self.repos(filter_)
        if len( repos) == 0: return
        repo_names = [r.name for r in repos]
        response = ask("Finish feature in these repositories?\n  " + "\n  ".join( repo_names), "(y/n)")
        response = response.lower().strip()

        if not response in ('n','no', 'y', 'yes'):
          error( "illegal response: %s" % response)
          return

        if response in ('n','no'):
          return

        for r in repos:
            info(" finish feature for repository: %s" % r.name)
            r.finish_feature( name)

    def foreach(self, fname, filter_=None, silent=False):
        """
        Execute a method on all repositories in subprocesses.
        """
        repos = list(self.repos(filter_))

        if not repos:
            return

        _pool = Pool(len(repos))

        results = {}
        bars = {}
        barlist = []

        justification = max(len(p.name) for p in repos)

        for repo in repos:
            name = repo.name
            path = repo.path
            result = _pool.apply_async(doit, (repo, fname))
            results[path] = result
            bars[path] = GitProgressBar(name, justification)
            barlist.append(bars[path])

        _pool.close()

        barlist.sort(key=lambda bar:bar.name.count('/'))

        def ready():
            done = []
            for path, result in results.iteritems():
                if result.ready():
                    bars[path].done()
                    done.append(path)
            for d in done:
                del results[d]
            return not results

        printer = Reprinter()
        start = time.time()

        REFRESHINTERVAL = 0.1

        def printscreen():
            text = ''
            for bar in barlist:
                text += bar.get() + '\n'
            if not silent:
                printer.reprint(text)

        updated = True

        printscreen()

        while True:
            text = ''
            try:
                qresult = MultiprocessingProgress.QUEUE.get(timeout=0.1)
                (op_code, cur_count, max_count, msg), _, path = qresult
                bars[path].update(op_code, cur_count, max_count)
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
