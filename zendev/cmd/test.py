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


def serviced_tests(args, env, smoke=False):
    env = env()
    envvars = os.environ.copy()
    envvars.update(env.envvars())
    repo = env.repos(lambda x: x.name.endswith('control-center/serviced'))[0]
    cmd = ["make", "smoketest"] if smoke else ["make", "test"]
    cmd.extend(args.arguments[1:])
    with repo.path.as_cwd():
        return subprocess.call(cmd, env=envvars)


def test(args, env):
    rcs = []

    if args.devimg:
        rc = zen_image_tests(args, env, devimg=True)
    elif args.resmgr:
        rc = zen_image_tests(args, env, resmgr=True)
    elif args.core:
        rc = zen_image_tests(args, env)
    rcs.append(rc)

    if args.serviced_unit:
        rc = serviced_tests(args, env, smoke=False)
        rcs.append(rc)

    if args.serviced_smoke:
        rc = serviced_tests(args, env, smoke=True)
        rcs.append(rc)

    if not rcs:
        sys.exit("No tests were specified.")

    if any(rcs):
        sys.exit("Some tests failed.")


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
    test_parser.add_argument('-u', '--serviced', action="store_true",
            help="Run serviced unit tests",
            dest="serviced_unit", default=False)
    test_parser.add_argument('-s', '--serviced-smoke', action="store_true",
            help="Run serviced smoke tests",
            dest="serviced_smoke", default=False)
    #test_parser.add_argument('--with-consumer', action="store_true",
    #        help="Run metric-consumer unit tests",
    #        dest="with_consumer", default=False)
    #test_parser.add_argument('--with-query', action="store_true",
    #        help="Run query unit tests",
    #        dest="with_query", default=False)
    #test_parser.add_argument('--with-zep', action="store_true",
    #        help="Run ZEP unit tests",
    #        dest="with_zep", default=False)
    test_parser.add_argument('arguments', nargs=argparse.REMAINDER)

    test_parser.set_defaults(functor=test)
