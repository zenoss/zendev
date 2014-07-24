#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import os
import sys
import io
import re
import argparse
import time
import argcomplete
import subprocess
from contextlib import contextmanager
import json

import py

from .log import error
from .config import get_config
from .utils import colored, here
from .manifest import create_manifest
from . import config as zcfg
from . import environment as zenv
from .environment import ZenDevEnvironment, init_config_dir
from .environment import NotInitialized
from .box import BOXES
from .serviced import Serviced


def get_envname():
    return get_config().current

class fargs(object):
    pass

@contextmanager
def temp_env():
    """
    Creates a temporary environment and patches everything to use it for the
    lifespan of the context manager.
    """
    td = py.path.local.mkdtemp()
    _old, zenv.CONFIG_DIR = zenv.CONFIG_DIR, td.join('config')
    _old, zcfg.CONFIG_DIR = zcfg.CONFIG_DIR, td.join('config')
    _zdebash, ZenDevEnvironment.bash = ZenDevEnvironment.bash, lambda *x:None
    path = td.join('root')
    args = fargs()
    args.path = path.strpath
    args.default_repos = False
    args.tag = None
    env = init(args)
    os.environ.update(env.envvars())
    yield
    zenv.CONFIG_DIR = _old
    zcfg.CONFIG_DIR = _old
    ZenDevEnvironment.bash = _zdebash


def check_env(name=None, **kwargs):
    envname = name or get_envname()
    if envname is None:
        error("Not in a zendev environment. Run 'zendev init' or 'zendev use'.")
        sys.exit(1)
    if not get_config().exists(envname):
        error("Zendev environment %s does not exist." % envname)
        sys.exit(1)

    try:
        return ZenDevEnvironment(envname, **kwargs)
    except NotInitialized:
        error("Not a zendev environment. Run 'zendev init' first.")
        sys.exit(1)


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


def bootstrap(args):
    print here("bootstrap.sh").strpath


def root(args):
    env = check_env()
    print env.root.strpath


def selfupdate(args):
    with here().as_cwd():
        subprocess.call(["git", "pull"])


def serviced(args):
    timeout = 60
    serviced = Serviced(check_env())
    if args.reset:
        serviced.reset()
    if args.arguments and args.arguments[0] == '--':
        args.arguments = args.arguments[1:]
    if args.root:
        print >>sys.stderr, "--root is deprecated, as it is now the default. See --no-root."
    serviced.start(not args.no_root, args.uiport, args.arguments,
            registry=args.with_docker_registry)
    try:
        while not serviced.is_ready():
            if not timeout:
                print "Timed out waiting for serviced!"
                sys.exit(1)
            print "Not ready yet. Checking again in 1 second."
            time.sleep(1)
            timeout -= 1
        print "serviced is ready!"
        if args.deploy:
            serviced.add_host()
            tplid = serviced.add_template()
            if args.no_auto_assign_ips:
                serviced.deploy(template=tplid, noAutoAssignIpFlag="--manual-assign-ips")
            else:
                serviced.deploy(tplid)
        if args.startall:
            serviced.startall()
        # Join the subprocess
        serviced.wait()
    except Exception:
        serviced.stop()
        raise
    except (KeyboardInterrupt, SystemExit):
        serviced.stop()
        sys.exit(0)

def feature_start(args):
    """
    Start git flow feature for all requested repositories.
    """
    filter_ = None
    if args.repos:
        filter_ = args.repofilter
    check_env().start_feature(args.name, filter_)


def feature_list(args):
    """
    List git flow feature for all repositories.
    """
    check_env().list_feature(args.name)


def feature_pull(args):
    """
    Request github pull-request for repositories with feature name
    """
    filter_ = None
    if args.repos:
        filter_ = args.repofilter
    check_env().pull_feature(args.name, filter_)


def feature_finish(args):
    """
    finish all git repositories with feature name
    """
    filter_ = None
    if args.repos: filter_ = args.repofilter
    check_env().finish_feature(args.name, filter_)


def init(args):
    """
    Initialize an environment.
    """
    path = py.path.local().ensure(args.path, dir=True)
    name = args.path  # TODO: Better name-getting
    config = get_config()
    config.add(name, args.path)
    with path.as_cwd():
        try:
            env = ZenDevEnvironment(name=name, path=path)
        except NotInitialized:
            init_config_dir()
            env = ZenDevEnvironment(name=name, path=path)
        env.manifest.save()
        env.initialize()
        env.use()
    if args.tag:
        env.restore(args.tag)
    return env


def add(args, paths=()):
    """
    Add a manifest.
    """
    manifest = check_env().manifest
    manifest.merge(create_manifest(args.manifest or ()))
    manifest.save()


def remove(args):
    """
    Remove a repository.
    """
    env = check_env()
    if not args.repos:
        error("No repositories were specified.")
        sys.exit(1)
    env.remove(args.repofilter)


def freeze(args):
    """
    Output JSON representation of manifests.
    """
    print check_env().freeze()


def ls(args):
    """
    Output information about repositories.
    """
    config = get_config()
    cur = get_envname()
    for env in config.environments:
        prefix = colored('*', 'blue') if env==cur else ' '
        print prefix, env


def box_create(args):
    """
    """
    env = check_env()
    env.vagrant.create(args.name, args.type, args.btrfs, args.vfs, args.memory)
    env.vagrant.provision(args.name, args.type)
    env.vagrant.ssh(args.name)


def box_remove(args):
    env = check_env()
    env.vagrant.remove(args.name)


def box_ssh(args):
    check_env().vagrant.ssh(args.name)


def box_up(args):
    check_env().vagrant.up(args.name)


def box_halt(args):
    check_env().vagrant.halt(args.name)


def box_ls(args):
    check_env().vagrant.ls()


def cluster_create(args):
    """
    """
    env = check_env()
    env.cluster.create(args.name, args.type, args.count, args.domain, args.memory)
    env.cluster.provision(args.name, args.type)


def cluster_remove(args):
    env = check_env()
    env.cluster.remove(args.name)


def cluster_ssh(args):
    check_env().cluster.ssh(args.name, args.box)


def cluster_boot(args):
    check_env().cluster.boot(args.name)


def cluster_up(args):
    check_env().cluster.up(args.name, args.box)


def cluster_shutdown(args):
    check_env().cluster.shutdown(args.name)


def cluster_halt(args):
    check_env().cluster.halt(args.name, args.box)


def cluster_ls(args):
    check_env().cluster.ls()


def restore(args):
    check_env().restore(args.name)


def restoreCompleter(prefix, **kwargs):
    return (x for x in check_env().list_tags() if x.startswith(prefix))


def tag(args):
    if args.list:
        for tag in check_env().list_tags():
            print tag
    elif args.delete:
        if not args.name:
            error("Missing the name of a tag to delete")
            sys.exit(1)
        elif args.name == 'develop':
            error("You can't delete develop!")
            sys.exit(1)
        check_env().tag_delete(args.name)
    else:
        if not args.name:
            error("Missing the name of a tag to create")
            sys.exit(1)
        check_env().tag(args.name, args.strict, args.force, args.from_ref)


def cd(args):
    """
    Print the directory of the repository if specified or the environment if not.
    """
    env = check_env()
    if args.repo:
        repos = check_env().repos(repofilter([args.repo]))
        if not repos:
            # try to fall back to a directory in our srcroot
            nonRepoPath = env.srcroot.join(args.repo).strpath
            if os.path.isdir(nonRepoPath):
                env.bash('cd "%s"' % nonRepoPath)
                return
            else:
                error("No repo matching %s found" % args.repo)
                sys.exit(1)
        for repo in repos:
            if repo.path.strpath.endswith(args.repo.strip()):
                env.bash('cd "%s"' % repo.path.strpath)
                return
        env.bash('cd "%s"' % repos[0].path.strpath)
    else:
        env.bash('cd "%s"' % env._root.strpath)


def sync(args):
    """
    Clone or update any existing repositories, push any commits.
    """
    check_env().sync(args.repofilter)


def status(args):
    """
    Print status.
    """
    if args.repos:
        filter_ = args.repofilter
    elif args.all:
        filter_ = None
    else:
        filter_ = lambda r: not r.path.check() or any(r.changes)
    check_env().status(filter_)


def each(args):
    """
    Execute a command in each repo's directory.
    """
    for repo in check_env().repos(args.repofilter):
        print repo.name
        with repo.path.as_cwd():
            subprocess.call(args.command)


def build(args):
    srcroot = None
    if args.manifest and not args.noenv:
        srcroot = py.path.local.mkdtemp()
    env = check_env(manifest=args.manifest, srcroot=srcroot)
    if args.tag:
        env.restore(args.tag, shallow=True)
    if args.manifest:
        env.clone(shallow=True)
    if args.createtag:
        env.tag(args.createtag, strict=True)
    if args.rps:
        os.environ['GA_IMAGE_TAG'] = args.ga_image
    os.environ.update(env.envvars())
    with env.buildroot.as_cwd():
        target = ['srcbuild' if t == 'src' else t for t in args.target]
        if args.clean:
            subprocess.call(["make", "clean"])
        rc = subprocess.call(["make", "OUTPUT=%s" % args.output] + target)
        sys.exit(rc)


def changelog(args):
    buf = io.StringIO()
    env = check_env()
    try:
        frommanifest = env.get_manifest(args.tag1)
    except Exception:
        error("%s is an invalid tag. See available tags with `zendev tag --list`" % args.tag1)
        sys.exit(1)
    try:
        tomanifest = env.get_manifest(args.tag2) if args.tag2 else env.manifest
    except Exception:
        error("%s is an invalid tag. See available tags with `zendev tag --list`" % args.tag2)
        sys.exit(1)
    for repo in env.repos():
        ref1 = frommanifest._data['repos'].get(repo.name, {}).get('ref')
        ref2 = tomanifest._data['repos'].get(repo.name, {}).get('ref')
        if not ref1 or not ref2 or ref1 == ref2:
            continue
        result = repo.changelog(ref1, ref2)
        if result:
            buf.write(u"""
{repo_name} | {repo_url}
=============================================================================
{changelog}
""".format(repo_name=repo.name, repo_url=repo.url, changelog=result))
    full_log = buf.getvalue().strip()
    if sys.stdout.isatty():
        p = subprocess.Popen(["less"], stdin=subprocess.PIPE)
        p.communicate(full_log)
        p.wait()
    else:
        print full_log


def attach(args):
    print >>sys.stderr, "Yo, you can probably just use serviced attach"
    subprocess.call("serviced service attach '%s'; stty sane" % args.specifier,
                    shell=True)

def devshell(args):
    env = check_env()
    cmd = "docker run -v %s/src:/mnt/src -v %s:/opt/zenoss -i -t zendev/devimg bash" % (env.root.strpath, env.root.join("zenhome").strpath)
    subprocess.call(cmd, shell=True)

def clone(args):
    env = ZenDevEnvironment(srcroot=args.output, manifest=args.manifest)
    if args.tag:
        env.restore(args.tag, shallow=args.shallow)
    else:
        env.clone(shallow=args.shallow)


def use(args):
    """
    Use a zendev environment.
    """
    check_env(args.name).use()


def drop(args):
    """
    Drop a zendev environment.
    """
    get_config().remove(args.name, not args.purge)


def zup(args):
    """
    Do zup-related things like build zups, which is a blast.
    """
    with check_env().buildroot.as_cwd():
        rc = subprocess.call(["make",
                              "GA_BUILD_IMAGE={}".format(args.begin_image),
                              "PRODUCT={}".format(args.product),
                              "zup"]
        )
        sys.exit(rc)

def add_repo_narg(parser):
    parser.add_argument('repos', nargs='*', help='List of repositories')


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--script', action='store_true',
                        help=argparse.SUPPRESS)

    parser.add_argument('-n', '--noenv', action='store_true', 
                        help="Run in a temporary environment")

    subparsers = parser.add_subparsers(dest='subparser')

    zup_description = "Build a zup!  This will spawn a container that will talk " \
                      "to docker on the host machine running zendev.  Currently, " \
                      "the HOST param is ignored in favor of bind mounting the " \
                      "local host's unix socket into the container."
    zup_parser = subparsers.add_parser('zup', description=zup_description)
    zup_parser.add_argument("begin_image", help="The GA image that should be used as "
                                          "the baseline for building ZUPs.  "
                                          "Should be in the format "
                                          "'imageName:tag'")
    zup_parser.add_argument("--no-cleanup", help="Do NOT cleanup docker "
                                                 "containers created during "
                                                 "zup creation.  This should "
                                                 "really only be used for "
                                                 "debugging purposes, as you "
                                                 "will need to manually clean "
                                                 "up after yourself if you use"
                                                 "this flag.",
                            action="store_true", dest="cleanup")
    zup_parser.add_argument("product", help="Product to build a zup for",
                            choices=['zenoss-5.0.0'])

    zup_parser.set_defaults(functor=zup)

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('path', metavar="PATH")
    init_parser.add_argument('-t', '--tag', metavar="TAG", required=False)
    init_parser.set_defaults(functor=init)

    use_parser = subparsers.add_parser('use')
    use_parser.add_argument('name', metavar='ENVIRONMENT')
    use_parser.set_defaults(functor=use)

    build_parser = subparsers.add_parser('build')
    build_parser.add_argument('-t', '--tag', metavar='TAG', required=False)
    build_parser.add_argument('-m', '--manifest', nargs="+",
                              metavar='MANIFEST', required=False)
    build_parser.add_argument('-o', '--output', metavar='DIRECTORY',
                              default=py.path.local().join('output').strpath)
    build_parser.add_argument('-c', '--clean', action="store_true",
                              default=False)
    build_parser.add_argument('--create-tag', dest="createtag", required=False,
                              help="Tag the source for this build")
    build_parser.add_argument('--rps', action="store_true",
                              help="Build an RPS image (requires the --ga_image argument)")
    build_parser.add_argument('--ga_image', help="When building an RPS image, "
                                                 "specify the GA image tag to use")
    build_parser.add_argument('target', metavar='TARGET', nargs="+",
                              choices=['src', 'core', 'resmgr',
                                       'svcdef-core', 'svcdef-resmgr',
                                       'svcdefpkg-core', 'svcdefpkg-resmgr',
                                       'svcpkg-core', 'svcpkg-resmgr', 'svcpkg',
                                       'serviced', 'devimg', 'img-core',
                                       'img-resmgr', 'rps-img-core',
                                       'rps-img-resmgr'])
    build_parser.set_defaults(functor=build)

    devshell_parser = subparsers.add_parser('devshell')
    devshell_parser.set_defaults(functor=devshell)

    drop_parser = subparsers.add_parser('drop')
    drop_parser.add_argument('name', metavar='ENVIRONMENT')
    drop_parser.add_argument('--purge', action="store_true")
    drop_parser.set_defaults(functor=drop)

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('manifest', nargs='+', metavar="MANIFEST")
    add_parser.set_defaults(functor=add)

    rm_parser = subparsers.add_parser('rm')
    add_repo_narg(rm_parser)
    rm_parser.set_defaults(functor=remove)

    ls_parser = subparsers.add_parser('ls')
    ls_parser.set_defaults(functor=ls)

    cd_parser = subparsers.add_parser('cd')
    cd_parser.add_argument('repo', nargs='?', metavar="REPO")
    cd_parser.set_defaults(functor=cd)

    freeze_parser = subparsers.add_parser('freeze')
    freeze_parser.set_defaults(functor=freeze)

    sync_parser = subparsers.add_parser('sync')
    add_repo_narg(sync_parser)
    sync_parser.set_defaults(functor=sync)

    status_parser = subparsers.add_parser('status')
    status_parser.add_argument('-a', '--all', action='store_true', 
        help="Display all repos, whether or not they have changes.")
    add_repo_narg(status_parser)
    status_parser.set_defaults(functor=status)

    clone_parser = subparsers.add_parser('clone')
    clone_parser.add_argument('-t', '--tag', metavar='TAG',
            help="Manifest tag to restore")
    clone_parser.add_argument('-m', '--manifest', nargs='+',
            metavar='MANIFEST', help="Manifest to use")
    clone_parser.add_argument('-s', '--shallow', action='store_true',
            help="Only check out the most recent commit for each repo")
    clone_parser.add_argument('output', metavar='SRCROOT',
            help="Target directory into which to clone")
    clone_parser.set_defaults(functor=clone)

    #feature parser
    feature_parser = subparsers.add_parser('feature')
    feature_subparser = feature_parser.add_subparsers()

    feature_start_parser = feature_subparser.add_parser('start', help='Start feature branch on specified '
                                                                      'repositories')
    feature_start_parser.add_argument('name', help='Name of the feature branch')
    add_repo_narg(feature_start_parser)
    feature_start_parser.set_defaults(functor=feature_start)

    feature_start_parser = feature_subparser.add_parser('list', help="List all repos containing the specified "
                                                                     "feature branch")
    feature_start_parser.add_argument('name', help='Name of the feature branch')
    feature_start_parser.set_defaults(functor=feature_list)

    feature_pull_parser = feature_subparser.add_parser('pull', help="Create pull request for feature branch")
    feature_pull_parser.add_argument('name', help='Name of the feature branch')
    add_repo_narg(feature_pull_parser)
    feature_pull_parser.set_defaults(functor=feature_pull)

    feature_finish_parser = feature_subparser.add_parser('finish', help='Finish the feature branch')
    feature_finish_parser.add_argument('name', help="Name of the feature branch")
    add_repo_narg(feature_finish_parser)
    feature_finish_parser.set_defaults(functor=feature_finish)

    each_parser = subparsers.add_parser('each')
    each_parser.add_argument('-r', '--repo', dest="repos", nargs='*')
    each_parser.add_argument('command', nargs="*")
    each_parser.set_defaults(functor=each)

    cluster_parser = subparsers.add_parser('cluster')
    cluster_subparsers = cluster_parser.add_subparsers()

    cluster_create_parser = cluster_subparsers.add_parser('create')
    cluster_create_parser.add_argument('name', metavar="NAME")
    cluster_create_parser.add_argument('--type', required=True, choices=BOXES)
    cluster_create_parser.add_argument('--count', type=int, default=1)
    cluster_create_parser.add_argument('--memory', type=int, default=4096)
    cluster_create_parser.add_argument('--domain', default='zenoss.loc')
    cluster_create_parser.set_defaults(functor=cluster_create)

    cluster_boot_parser = cluster_subparsers.add_parser('boot')
    cluster_boot_parser.add_argument('name', metavar="NAME")
    cluster_boot_parser.set_defaults(functor=cluster_boot)

    cluster_up_parser = cluster_subparsers.add_parser('up')
    cluster_up_parser.add_argument('name', metavar="NAME")
    cluster_up_parser.add_argument('box', metavar="BOX")
    cluster_up_parser.set_defaults(functor=cluster_up)

    cluster_shutdown_parser = cluster_subparsers.add_parser('shutdown')
    cluster_shutdown_parser.add_argument('name', metavar="NAME")
    cluster_shutdown_parser.set_defaults(functor=cluster_shutdown)

    cluster_halt_parser = cluster_subparsers.add_parser('halt')
    cluster_halt_parser.add_argument('name', metavar="NAME")
    cluster_halt_parser.add_argument('box', metavar="BOX")
    cluster_halt_parser.set_defaults(functor=cluster_halt)

    cluster_remove_parser = cluster_subparsers.add_parser('destroy')
    cluster_remove_parser.add_argument('name', metavar="NAME")
    cluster_remove_parser.set_defaults(functor=cluster_remove)

    cluster_ssh_parser = cluster_subparsers.add_parser('ssh')
    cluster_ssh_parser.add_argument('name', metavar="NAME")
    cluster_ssh_parser.add_argument('box', metavar="BOX")
    cluster_ssh_parser.set_defaults(functor=cluster_ssh)

    cluster_ls_parser = cluster_subparsers.add_parser('ls')
    cluster_ls_parser.set_defaults(functor=cluster_ls)

    box_parser = subparsers.add_parser('box')
    box_subparsers = box_parser.add_subparsers()

    box_create_parser = box_subparsers.add_parser('create')
    box_create_parser.add_argument('name', metavar="NAME")
    box_create_parser.add_argument('--type', required=True, choices=BOXES)
    box_create_parser.add_argument('--btrfs', type=int, default=0)
    box_create_parser.add_argument('--vfs', type=int, default=0)
    box_create_parser.add_argument('--memory', default="1024*8",
                                  help="memory in mb")
    box_create_parser.set_defaults(functor=box_create)

    box_up_parser = box_subparsers.add_parser('up')
    box_up_parser.add_argument('name', metavar="NAME")
    box_up_parser.set_defaults(functor=box_up)

    box_halt_parser = box_subparsers.add_parser('halt')
    box_halt_parser.add_argument('name', metavar="NAME")
    box_halt_parser.set_defaults(functor=box_halt)

    box_remove_parser = box_subparsers.add_parser('destroy')
    box_remove_parser.add_argument('name', metavar="NAME")
    box_remove_parser.set_defaults(functor=box_remove)

    box_ssh_parser = box_subparsers.add_parser('ssh')
    box_ssh_parser.add_argument('name', metavar="NAME")
    box_ssh_parser.set_defaults(functor=box_ssh)

    box_ls_parser = box_subparsers.add_parser('ls')
    box_ls_parser.set_defaults(functor=box_ls)

    restore_parser = subparsers.add_parser('restore')
    a = restore_parser.add_argument('name', metavar="NAME")
    a.completer = restoreCompleter
    restore_parser.set_defaults(functor=restore)

    tag_parser = subparsers.add_parser('tag')
    tag_parser.add_argument('--strict', action="store_true")
    tag_parser.add_argument('-l', '--list', action="store_true")
    tag_parser.add_argument('-f', '--force', action="store_true")
    tag_parser.add_argument('-D', '--delete', action="store_true")
    tag_parser.add_argument('-F', '--from', dest="from_ref", required=False)
    a = tag_parser.add_argument('name', metavar="NAME", nargs="?")
    a.completer = restoreCompleter
    tag_parser.set_defaults(functor=tag)

    changelog_parser = subparsers.add_parser('changelog')
    changelog_parser.add_argument('tag1', metavar="TAG").completer = restoreCompleter
    changelog_parser.add_argument('tag2', metavar="TAG", nargs="?").completer = restoreCompleter
    changelog_parser.set_defaults(functor=changelog)

    ssh_parser = subparsers.add_parser('ssh')
    ssh_parser.add_argument('name', metavar="NAME")
    ssh_parser.set_defaults(functor=box_ssh)

    bootstrap_parser = subparsers.add_parser('bootstrap')
    bootstrap_parser.set_defaults(functor=bootstrap)

    root_parser = subparsers.add_parser('root')
    root_parser.set_defaults(functor=root)

    serviced_parser = subparsers.add_parser('serviced')
    serviced_parser.add_argument('-r', '--root', action='store_true',
        help="Run serviced as root (DEPRECATED. Currently ignored; see --no-root)")
    serviced_parser.add_argument('-d', '--deploy', action='store_true',
        help="Add Zenoss service definitions and deploy an instance")
    serviced_parser.add_argument('-a', '--startall', action='store_true',
        help="Start all services once deployed")
    serviced_parser.add_argument('-x', '--reset', action='store_true',
        help="Clean service state and kill running containers first")
    serviced_parser.add_argument('--no-root', dest="no_root",
            action='store_true', help="Don't run serviced as root")
    serviced_parser.add_argument('--no-auto-assign-ips', action='store_true',
        help="Do NOT auto-assign IP addresses to services requiring an IP address")
    serviced_parser.add_argument('--with-docker-registry', action='store_true', default=False,
        help="Use the internal docker registry (necessary for multihost)")
    serviced_parser.add_argument('-u', '--uiport', type=int, default=443,
        help="UI port")
    serviced_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    serviced_parser.set_defaults(functor=serviced)

    update_parser = subparsers.add_parser('selfupdate')
    update_parser.set_defaults(functor=selfupdate)

    attach_parser = subparsers.add_parser('attach')
    attach_parser.add_argument('specifier', metavar="SERVICEID|SERVICENAME|DOCKERID",
        help="Attach to a container matching SERVICEID|SERVICENAME|DOCKERID in service instances")
    attach_parser.set_defaults(functor=attach)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Doing this here instead of in the functor because I want access to the
    # parser to properly throw the parsing error
    if args.subparser == 'build':
        if (args.rps or args.ga_image) and not (args.rps and args.ga_image):
            build_parser.error("The --rps and --ga_image arguments must be used together")
        # Enforce using --rps with an rps-img-% target
        if (args.rps and not any(t.startswith('rps-img-') for t in args.target)) or \
                (not args.rps and any(t.startswith('rps-img-') for t in args.target)):
            build_parser.error("Must call an 'rps-img-%' target with the --rps arg")

    if hasattr(args, 'repos'):
        args.repofilter = repofilter(args.repos or ())

    return args


def main():
    args = parse_args()
    if args.noenv:
        with temp_env():
            args.functor(args)
    else:
        args.functor(args)


if __name__ == "__main__":
    main()
