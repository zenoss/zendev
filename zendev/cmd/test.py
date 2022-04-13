from __future__ import absolute_import, print_function

import argparse
import os
import subprocess
import sys

from ..devimage import DevImage


def test(args, env):
    environ = env()
    environ.productAssembly.chdir()

    if not os.path.exists("test_image.sh"):
        return _old_test(args, env)

    cmd = ["./test_image.sh"]
    # PATH required for Docker integration with GCP
    envvars = {"PATH": os.environ["PATH"]}

    devImage = DevImage(environ)
    mounts = devImage.get_mounts()
    for mount in mounts.items():
        cmd.extend(["--mount", "%s:%s" % mount])

    cmd.extend(["--env", "SRCROOT=/mnt/src"])

    if args.interactive:
        cmd.append("--shell")
    else:
        cmd.extend(args.arguments[1:])

    productImageName = devImage.get_image_name()
    if not devImage.image_exists(productImageName):
        print(
            "You don't have the devimg built. Please run"
            '"zendev devimg" first.',
            file=sys.stderr,
        )
        sys.exit(1)
    envvars["PRODUCT_IMAGE_ID"] = productImageName

    mariadbImageName = devImage.get_mariadb_name()
    if not devImage.image_exists(mariadbImageName):
        print(
            "You don't have the mariadb image built. Please run"
            '"zendev devimg" first.',
            file=sys.stderr,
        )
        sys.exit(1)
    envvars["MARIADB_IMAGE_ID"] = mariadbImageName

    devimgSrcDir = environ.productAssembly
    devimgSrcDir.chdir()
    print(" ".join(cmd))
    subprocess.Popen(cmd, env=envvars).wait()


def _old_test(args, env):
    cmd = ["docker", "run", "-i", "-t", "--rm"]
    if args.no_tty:
        cmd.remove("-t")

    environ = env()
    environ.generateZVersions()
    devImage = DevImage(environ)
    mounts = devImage.get_mounts()
    for mount in mounts.items():
        cmd.extend(["-v", "%s:%s" % mount])

    imageName = devImage.get_image_name()
    if not devImage.image_exists(imageName):
        print(
            "You don't have the devimg built. Please run "
            '"zendev devimg" first.',
            file=sys.stderr,
        )
        sys.exit(1)
    cmd.append(imageName)

    if args.interactive:
        cmd.append("bash")
    else:
        cmd.append("/opt/zenoss/install_scripts/starttests.sh")
        cmd.extend(args.arguments[1:])

    print("Using %s image." % imageName)
    print("Calling Docker with the following:")
    print(" ".join(cmd))
    if subprocess.call(cmd):
        sys.exit(1)


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
    test_parser.add_argument(
        "-n",
        "--no-tty",
        action="store_true",
        default=False,
        dest="no_tty",
        help="Do not allocate a TTY",
    )
    test_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    test_parser.set_defaults(functor=test)
