import argparse
import subprocess
import sys
import os

from zendev.cmd.build import get_resmgr_packs


def check_devimg():
    has_devimg = subprocess.call(["test", "-n",
                                  '"$(docker images -q zendev/devimg)"'],
                                 shell=True)
    if not has_devimg:
        print >> sys.stderr, ("You don't have the devimg built. Please run"
                              " zendev build devimg\" first.")
        sys.exit(1)


def build_image(args, env, resmgr=False):
    pass


def get_packs(env, resmgr=False):
    return get_resmgr_packs(env) if resmgr else [
            "ZenPacks.zenoss.ZenJMX", "ZenPacks.zenoss.PythonCollector"]


def zen_image_tests(args, env, devimg=False, resmgr=False):
    env = env()
    envvars = os.environ.copy()
    envvars.update(env.envvars())
    mounts = {envvars["SRCROOT"]: "/mnt/src"}
    if devimg:
        check_devimg()
        image = "zendev/devimg"
        mounts[os.path.join(envvars["HOME"], ".m2")] = "/home/zenoss/.m2"
        mounts[os.path.join(envvars["ZENHOME"])] = "/opt/zenoss"
    else:
        # Run a build
        envvars['DEVIMG_SYMLINK'] = ''
        envvars['devimg_MOUNTS'] = ''
        envvars['devimg_TAGNAME'] = 'zendev_test'
        envvars['devimg_CONTAINER'] = 'zendev_test'
        envvars['ZENPACKS'] = ' '.join(get_packs(env, resmgr))
        with env.buildroot.as_cwd():
            rc = subprocess.call(["make", "devimg"], env=envvars)
            if rc > 0:
                return rc
        image = "zendev_test"
    cmd = ["docker", "run", "--rm"]
    for mount in mounts.iteritems():
        cmd.extend(["-v", "%s:%s" % mount])
    cmd.extend([image, "/usr/bin/run_tests.sh"])
    cmd.extend(args.arguments[1:])
    return subprocess.call(cmd)


def serviced_tests(args, env, integration=False):
    pass


def serviced_smoke_tests(args, env):
    pass


def test(args, env):

    rc = 0
    if args.devimg:
        rc = zen_image_tests(args, env, devimg=True)
    elif args.resmgr:
        rc = zen_image_tests(args, env, resmgr=True)
    elif args.core:
        rc = zen_image_tests(args, env)

    if rc > 0:
        sys.exit(rc)

    if args.serviced_int:
        serviced_tests(args, env, integration=True)
    elif args.serviced_unit:
        serviced_tests(args, env, integration=False)

    if args.serviced_smoke:
        serviced_smoke_tests(args, env)


    #srcroot = None
    #if args.manifest and not args.noenv:
    #    srcroot = py.path.local.mkdtemp()
    #env = env(manifest=args.manifest, srcroot=srcroot)
    #if args.tag:
    #    env.restore(args.tag, shallow=True)
    #if args.manifest:
    #    env.clone(shallow=True)
    #if args.createtag:
    #    env.tag(args.createtag, strict=True)
    #if args.rps:
    #    os.environ['GA_IMAGE_TAG'] = args.ga_image
    #    _manifestHash = env.ensure_manifestrepo().hash[:7]
    #    os.environ['TAG_HASH'] = _manifestHash
    #os.environ.update(env.envvars())
    #with env.buildroot.as_cwd():
    #    target = ['srcbuild' if t == 'src' else t for t in args.target]
    #    if args.clean:
    #        subprocess.call(["make", "clean"])
    #        bashcommand = "find /mnt/src/ -maxdepth 2 -name pom.xml|while read file; do (cd $(dirname $file) && echo -n cleaning: && pwd && mvn clean); done"
    #        cmd = "docker run --privileged --rm -v %s/src:/mnt/src -i -t zenoss/rpmbuild:centos7 bash -c '%s'" % (
    #                env.root.strpath, bashcommand)
    #        subprocess.call(cmd, shell=True)
    #    packs = get_resmgr_packs(env) if args.resmgr else ["ZenPacks.zenoss.ZenJMX", "ZenPacks.zenoss.PythonCollector"]
    #    if "devimg" in target:
    #        # Figure out which zenpacks to install.
    #        for pack in args.packs:
    #            if not pack.startswith("ZenPacks"):
    #                pack = "ZenPacks.zenoss." + pack
    #                packs.append(pack)
    #    # CatalogService is not currently compatible with zendev
    #    if "ZenPacks.zenoss.CatalogService" in packs:
    #        packs.remove("ZenPacks.zenoss.CatalogService")
    #    rc = subprocess.call(["make", "OUTPUT=%s" % args.output,
    #                          'ZENPACKS=%s' % ' '.join(packs)] + target)
    #    sys.exit(rc)


def add_commands(subparsers):
    test_parser = subparsers.add_parser('test', help="Run tests")

    test_parser.add_argument('-d', '--zenoss-devimg', action="store_true",
            help="Run Zenoss unit tests using the current devimg instance",
            dest="devimg", default=False)
    test_parser.add_argument('-r', '--zenoss-resmgr', action="store_true",
            help="Build a resmgr image and run Zenoss unit tests",
            dest="resmgr", default=False)
    test_parser.add_argument('-c', '--zenoss-core', action="store_true",
            help="Build a core image and run Zenoss unit tests",
            dest="core", default=False)
    test_parser.add_argument('-u', '--serviced-unit', action="store_true",
            help="Run serviced unit tests",
            dest="serviced_unit", default=False)
    test_parser.add_argument('-i', '--serviced-integration',
            help="Run serviced unit and integration tests",
            action="store_true", dest="serviced_int", default=False)
    test_parser.add_argument('-s', '--serviced-smoke', action="store_true",
            help="Run serviced smoke tests",
            dest="serviced_smoke", default=False)
    test_parser.add_argument('--with-consumer', action="store_true",
            help="Run metric-consumer unit tests",
            dest="with_consumer", default=False)
    test_parser.add_argument('--with-query', action="store_true",
            help="Run query unit tests",
            dest="with_query", default=False)
    test_parser.add_argument('--with-zep', action="store_true",
            help="Run ZEP unit tests",
            dest="with_zep", default=False)
    test_parser.add_argument('arguments', nargs=argparse.REMAINDER)

    test_parser.set_defaults(functor=test)
