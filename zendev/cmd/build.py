import subprocess
import sys
import os
import re
import tempfile
import uuid
import py

packlists = {
        'resmgr': 'pkg/zenoss_resmgr_zenpacks.mk',
        'ucspm': 'pkg/zenoss_ucspm_zenpacks.mk',
    }

def build(args, env):
    if "impact-devimg" in args.target:
        build_impact(args, env)
    else:
        build_zenoss(args, env)

def build_zenoss(args, env):
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

        product = ''
        if args.resmgr:
            product = 'resmgr'
        elif args.ucspm:
            product = 'ucspm'

        packs = get_packs(env, product)

        if "devimg" in target:
            os.environ['VAR_ZENOSS']=env.var_zenoss.strpath
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


def build_impact(args, env):
    impact_image = 'zenoss/impact-unstable:latest'
    container_id='impact_devimg_'+uuid.uuid1().hex
    # TODO: embedding the version number in the link means that we have do rebuild the image
    #  if the version changes.  Better if the pom.xml set up a non-versioned symlink to the
    # versioned file; then this could link to the non-versioned symlink.
    startup="""
        SRC=/mnt/src/impact/impact-server
        DST=/opt/zenoss_impact
        VSN=4.2.6.70.0-SNAPSHOT
        ln -fs $SRC/zenoss-dsa/target/zenoss-dsa-$VSN.war $DST/webapps/impact-server.war
        ln -fs $SRC/model-adapters-common/target/model-adapters-common-$VSN.jar $DST/lib/ext/adapters
        ln -fs $SRC/model-adapters-zenoss/target/model-adapters-zenoss-$VSN.jar $DST/lib/ext/adapters/zenoss
    """
    with tempfile.NamedTemporaryFile() as f:
        f.write(startup)
        f.flush()
        cmd = 'docker run -v %s:/root/impact_devimg_init --name %s %s /bin/sh /root/impact_devimg_init' % (
            f.name,
            container_id,
            impact_image
        )
        subprocess.call(cmd, shell=True)
    subprocess.call('docker commit %s %s' % (container_id, impact_image), shell=True)
    subprocess.call('docker rm %s' % container_id, shell=True)

zpline = re.compile(r'^[ \t]*zenoss_(?P<product>\w+).zp_to_(?P<action>[\w_]*)[ \t]*\+?=[ \t]*(?P<pack>[\w\.]*)[ \t]*$')

def get_packs_from_mk(env, product):
    packs = []
    removepacks = []
    with env.buildroot.as_cwd():
        with open(packlists[product]) as f:
            for line in f:
                match = zpline.match(line)
                if match:
                    if match.group('action') == 'build':
                        packs.append(match.group('pack'))
                    elif match.group('action') == 'not_install':
                        removepacks.append(match.group('pack'))
    for pack in removepacks:
        if pack in packs:
            packs.remove(pack)
    return packs

def get_packs(env, product):
    packs = ["ZenPacks.zenoss.ZenJMX", "ZenPacks.zenoss.PythonCollector"]
    if product:
        packs = get_packs_from_mk(env, product)
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
            default=[],
            help="In a devimg build, ZenPacks to install into the image")
    build_parser.add_argument('--resmgr', action="store_true", required=False,
            help="Install resmgr ZenPacks")
    build_parser.add_argument('--ucspm', action="store_true", required=False,
            help="Install UCS-PM ZenPacks")
    build_parser.add_argument('target', metavar='TARGET', nargs="+",
                              choices=['src', 'core', 'resmgr', 'ucspm',
                                       'svcdef-core', 'svcdef-resmgr', 'svcdef-ucspm',
                                       'svcdefpkg-core', 'svcdefpkg-resmgr', 'svcdefpkg-ucspm',
                                       'svcpkg-core', 'svcpkg-resmgr', 'svcpkg-ucspm', 'svcpkg',
                                       'serviced', 'devimg', 'img-core',
                                       'img-resmgr', 'img-ucspm', 'rps-img-core',
                                       'rps-img-resmgr', 'rps-img-ucspm', 'impact-devimg'])
    build_parser.set_defaults(functor=build)

