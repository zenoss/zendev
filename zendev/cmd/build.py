import subprocess
import sys

from ..log import error, info


def build(args, env):
    """
    Build a Zenoss Product the same way the nightly build does.
    """

    targetDir = env().productAssembly.join(args.target_product)
    if not targetDir.check():
        error("%s does not exist" % targetDir.strpath)
        sys.exit(1)

    # This is just a simple sanity check to avoid building from subdirectories
    # of product-assembly which are NOT actually product directories
    zenpackManifestFile = targetDir.join("zenpacks.json")
    if not zenpackManifestFile.check():
        error(
            "Target product '%s' does not appear to be a valid product. "
            "Could not find %s"
            % (args.target_product, zenpackManifestFile.strpath),
        )
        sys.exit(1)

    zenservicemigrations = env().productAssembly.join("svcdefs")
    print "Building zenservicemigrations ..."
    print "cd %s" % zenservicemigrations.strpath
    zenservicemigrations.chdir()
    cmdArgs = ["make"]
    if args.clean:
        cmdArgs.append("clean")
    cmdArgs.append("migrations")
    print " ".join(cmdArgs)
    try:
        subprocess.check_call(cmdArgs)
    except Exception:
        info("zenservicemigration build not found, skipping.")

    cmdArgs = ["make"]
    if args.clean:
        cmdArgs.append("clean")
    cmdArgs.append("build")

    productBase = env().productAssembly.join("product-base")
    print "Building product-base ..."
    print "cd %s" % productBase.strpath
    productBase.chdir()
    print " ".join(cmdArgs)
    subprocess.check_call(cmdArgs)

    mariadbBase = env().productAssembly.join("mariadb-base")
    if mariadbBase.check():
        print "Building mariadb-base ..."
        print "cd %s" % mariadbBase.strpath
        mariadbBase.chdir()
        print " ".join(cmdArgs)
        subprocess.check_call(cmdArgs)

    print "Building %s" % args.target_product
    print "cd %s" % targetDir.strpath
    targetDir.chdir()
    print " ".join(cmdArgs)
    subprocess.check_call(cmdArgs)


def add_commands(subparsers):
    build_parser = subparsers.add_parser("build", help="Build Zenoss")
    build_parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        default=False,
        help="Delete any existing images before building",
    )
    build_parser.add_argument(
        "target_product",
        metavar="TARGET",
        help="Name of the target product to build; e.g. core, resmgr, etc",
    )
    build_parser.set_defaults(functor=build)
