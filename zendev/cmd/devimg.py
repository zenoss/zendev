import json
import py
import subprocess
import sys

from ..log import error


def devimg(args, env):
    """
    Build a developer image of Zenoss.

    All of the business logic for building a devimg is defined in the devimg subdirectory
    of the product-assembly repo.  All this command needs to do is invoke the make in
    product-assembly/devimg with the right arguments, which are mostly environment variables.
    See product-assembly/devimg/makefile for more details.

    For the zendev user, the primary choice is which set of zenpacks (if any) to
    include in the image. The options are: none, all of those specified for one
    of the products defined in product-assembly (e.g. core, resmgr, etc), the set
    of zenpacks defined in a custom zenpacks.json file, or simply an adhoc list
    defined on the zendev command line.
    """
    environ = env()
    environ.generateZVersions()

    cmdArgs = ['make']
    if args.clean:
        cmdArgs.append('clean')
    cmdArgs.append('build')
    cmdArgs.append("ZENDEV_ROOT=%s" % environ.root.strpath)
    cmdArgs.append("SRCROOT=%s" % environ.srcroot.join("github.com", "zenoss").strpath)
    cmdArgs.append('DEV_ENV=%s' % environ.name)
    if args.product:
        targetDir = environ.productAssembly.join(args.product)
        if not targetDir.check():
            error("%s does not exist" % targetDir.strpath)
            sys.exit(1)

        # This is just a simple sanity check to avoid building from subdirectories
        # of product-assembly which are NOT actually product directories
        zenpackManifestFile = targetDir.join("zenpacks.json")
        if not zenpackManifestFile.check():
            error("Target product '%s' does not appear to be a valid product. Could not find %s" % (args.target_product, zenpackManifestFile.strpath))
            sys.exit(1)
        cmdArgs.append("TARGET_PRODUCT=%s" % args.product)

    elif args.file:
        zenpackManifestFile = py._path.local.LocalPath(args.file)
        if not zenpackManifestFile.check():
            error("File '%s' does not exist" % zenpackManifestFile.strpath)
            sys.exit(1)
        cmdArgs.append("ZENPACK_FILE=%s" % zenpackManifestFile.strpath)

    elif args.zenpacks:
        zenpacks = args.zenpacks.split(",")
        cmdArgs.append("ZENPACK_FILE=%s" % _createZPFile(environ, zenpacks))

    else:
        print "Adding default ZenPacks.zenoss.PythonCollector..."
        cmdArgs.append("ZENPACK_FILE=%s" % _createZPFile(environ, ['ZenPacks.zenoss.PythonCollector']))

    print "Building devimg ..."
    devimgSrcDir = environ.productAssembly.join("devimg")
    print "cd %s" % devimgSrcDir.strpath
    devimgSrcDir.chdir()
    print " ".join(cmdArgs)
    subprocess.check_call(cmdArgs)

def _createZPFile(environ, zenpackList):
        zenpackManifestFile = environ.root.join("tmp/zenpacks.json")
        zenpackManifestFile.ensure()
        zenpacks = {}
        zenpacks['install_order'] = zenpackList
        with zenpackManifestFile.open("w") as jsonFile:
            json.dump(zenpacks, jsonFile, sort_keys=True, indent=4, separators=(',', ': '))
        return zenpackManifestFile.strpath

def add_commands(subparsers):
    devimg_parser = subparsers.add_parser('devimg',
        help='Build a developer image of Zenoss containing either no zenpacks, ' +
             'the set of zenpacks matching one of the standard products (core, resmgr, etc), ' +
             'or a custom set of zenpacks')
    devimg_parser.add_argument('-c', '--clean', action="store_true", default=False,
                              help='Delete any existing devimg before building a new one')
    zenpacks_parser = devimg_parser.add_mutually_exclusive_group(required=False)
    zenpacks_parser.add_argument('-p', '--product', metavar="PRODUCT", required=False,
                                 help='Name of a Zenoss product that defines the set of zenpacks copied into the image; e.g. core, resmgr, etc')
    zenpacks_parser.add_argument('-f', '--file',
                                 help='Path to a zenpacks.json file that defines the set of zenpacks copied into the image')
    zenpacks_parser.add_argument('-z', '--zenpacks', metavar="ZENPACKS", required=False,
                                 help='Comma-separated list of ZenPack names to copy into the image')

    devimg_parser.set_defaults(functor=devimg)
