import argparse
import subprocess
import sys
import os

from ..devimage import DevImage


def test(args, env):
    cmd = ["docker", "run", "-i", "-t", "--rm"]
    if args.no_tty:
        cmd.remove("-t")

    devImage = DevImage(env())
    mounts = devImage.get_mounts()
    for mount in mounts.iteritems():
        cmd.extend(["-v", "%s:%s" % mount])

    imageName = devImage.get_image_name()
    if not devImage.image_exists(imageName):
        print >> sys.stderr, ("You don't have the devimg built. Please run"
                              " zendev devimg\" first.")
        sys.exit(1)
    cmd.append(imageName)

    if args.interactive:
        cmd.append('bash')
    else:
        cmd.append("/opt/zenoss/install_scripts/starttests.sh")
        cmd.extend(args.arguments[1:])

    print "Using %s image." % imageName
    print "Calling Docker with the following:"
    print " ".join(cmd)
    return subprocess.call(cmd)


def add_commands(subparsers):
    test_parser = subparsers.add_parser('test', help="Run Zenoss product tests")

    test_parser.add_argument('-i', '--interactive', action="store_true",
            help="Start an interactive shell instead of running the test",
            default=False)
    test_parser.add_argument('-n', '--no-tty', action="store_true",
            help="Do not allocate a TTY",
            dest="no_tty",
            default=False)
    test_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    test_parser.set_defaults(functor=test)
