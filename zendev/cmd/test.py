import argparse
import subprocess
import sys

from ..devimage import DevImage


def test(args, env):
    environ = env()

    cmd = ["./test_image.sh"]
    envvars = {}

    devImage = DevImage(environ)
    mounts = devImage.get_mounts()
    for mount in mounts.iteritems():
        cmd.extend(["--mount", "%s:%s" % mount])

    cmd.extend(["--env", "SRCROOT=/mnt/src"])

    if args.interactive:
        cmd.append("--shell")
    else:
        cmd.extend(args.arguments[1:])

    productImageName = devImage.get_image_name()
    if not devImage.image_exists(productImageName):
        print >> sys.stderr, (
            "You don't have the devimg built. Please run"
            "'zendev devimg' first."
        )
        sys.exit(1)
    envvars["PRODUCT_IMAGE_ID"] = productImageName

    mariadbImageName = devImage.get_mariadb_name()
    if not devImage.image_exists(mariadbImageName):
        print >> sys.stderr, (
            "You don't have the mariadb image built. Please run"
            "'zendev devimg' first."
        )
        sys.exit(1)
    envvars["MARIADB_IMAGE_ID"] = mariadbImageName

    devimgSrcDir = environ.productAssembly
    devimgSrcDir.chdir()
    print " ".join(cmd)
    subprocess.Popen(cmd, env=envvars).wait()


def add_commands(subparsers):
    test_parser = subparsers.add_parser(
        "test", help="Run Zenoss product tests"
    )

    test_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start an interactive shell instead of running the test",
        default=False,
    )
    test_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    test_parser.set_defaults(functor=test)
