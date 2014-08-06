import os
import subprocess
import sys

import py


def zup(args, env):
    """
    Do zup-related things like build zups, which is a blast.
    """
    env = env(srcroot=None)
    if args.tag:
        env.restore(args.tag, shallow=True)
    _manifestHash = env.ensure_manifestrepo().hash[:7]
    with env.buildroot.as_cwd():
        rc = subprocess.call(["make",
                              "GA_BUILD_IMAGE={}".format(args.begin_image),
                              "PRODUCT={}".format(args.product),
                              "SRCROOT={}".format(os.path.join(
                                  env.root.strpath, 'src')
                              ),
                              "OUTPUT={}".format(args.output),
                              "TAG_HASH={}".format(_manifestHash),
                              "zup"]
        )
        sys.exit(rc)

def add_commands(subparsers):
    zup_description = "Build a zup!  This will spawn a container that will talk " \
                      "to docker on the host machine running zendev.  Currently, " \
                      "the HOST param is ignored in favor of bind mounting the " \
                      "local host's unix socket into the container."
    zup_parser = subparsers.add_parser('zup', description=zup_description)
    zup_parser.add_argument('-o', '--output', metavar='DIRECTORY',
                            default=py.path.local().join('output').strpath)
    zup_parser.add_argument('-t', '--tag', metavar='TAG', required=False,
                            help="Checkout a given manifest tag before building a zup.  "
                                 "Useful primarily for using a specific ref of platform-build "
                                 "(specified in the manifest) to do your zup building.")
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
