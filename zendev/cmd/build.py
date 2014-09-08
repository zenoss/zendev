import subprocess
import sys
import os

import py

def build(args, env):
    srcroot = None
    if args.manifest and not args.noenv:
        srcroot = py.path.local.mkdtemp()
    env = env(manifest=args.manifest, srcroot=srcroot)
    if args.tag:
        env.restore(args.tag, shallow=True)
    if args.manifest:
        env.clone(shallow=True)
    if args.createtag:
        env.tag(args.createtag, strict=True)
    if args.rps:
        os.environ['GA_IMAGE_TAG'] = args.ga_image
        _manifestHash = env.ensure_manifestrepo().hash[:7]
        os.environ['TAG_HASH'] = _manifestHash
    os.environ.update(env.envvars())
    with env.buildroot.as_cwd():
        target = ['srcbuild' if t == 'src' else t for t in args.target]
        if args.clean:
            subprocess.call(["make", "clean"])
            bashcommand = "find /mnt/src/ -maxdepth 2 -name pom.xml|while read file; do (cd $(dirname $file) && echo -n cleaning: && pwd && mvn clean); done"
            cmd = "docker run --privileged --rm -v %s/src:/mnt/src -i -t zenoss/rpmbuild:centos7 bash -c '%s'" % (
                    env.root.strpath, bashcommand)
            subprocess.call(cmd, shell=True)
        packs = get_resmgr_packs(env) if args.resmgr else ["ZenPacks.zenoss.ZenJMX", "ZenPacks.zenoss.PythonCollector"]
        if "devimg" in target:
            # Figure out which zenpacks to install.
            for pack in args.packs:
                if not pack.startswith("ZenPacks"):
                    pack = "ZenPacks.zenoss." + pack
                    packs.append(pack)
        # CatalogService is not currently compatible with zendev
        if "ZenPacks.zenoss.CatalogService" in packs:
            packs.remove("ZenPacks.zenoss.CatalogService")
        rc = subprocess.call(["make", "OUTPUT=%s" % args.output,
                              'ZENPACKS=%s' % ' '.join(packs)] + target)
        sys.exit(rc)


def get_resmgr_packs(env):
    packs = []
    with env.buildroot.as_cwd():
        with open("pkg/zenoss_resmgr_zenpacks.mk") as f:
            for line in f:
                if line.startswith("zenoss_resmgr.zp_to_build"):
                    pack = line.split()[-1]
                    packs.append(pack)
                elif line.startswith("zenoss_resmgr.zp_to_not_install"):
                    pack = line.split()[-1]
                    packs.remove(pack)
    return packs


def add_commands(subparsers):
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
    build_parser.add_argument('-p', '--with-pack', dest="packs", action="append",
            default=(),
            help="In a devimg build, ZenPacks to install into the image")
    build_parser.add_argument('--resmgr', action="store_true", required=False,
            help="Install resmgr ZenPacks")
    build_parser.add_argument('target', metavar='TARGET', nargs="+",
                              choices=['src', 'core', 'resmgr',
                                       'svcdef-core', 'svcdef-resmgr',
                                       'svcdefpkg-core', 'svcdefpkg-resmgr',
                                       'svcpkg-core', 'svcpkg-resmgr', 'svcpkg',
                                       'serviced', 'devimg', 'img-core',
                                       'img-resmgr', 'rps-img-core',
                                       'rps-img-resmgr'])
    build_parser.set_defaults(functor=build)

