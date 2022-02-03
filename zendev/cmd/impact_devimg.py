import subprocess
import uuid
import tempfile
from ..log import error


def impact_devimg(args, env):
    """
    Build a developer image of Zenoss Impact

    """
    if not args.impact_image:
        error(
            'missing required resource "impact-image" argument '
            "for building impact-devimg"
        )
        return
    impact_src_image = args.impact_image
    impact_dst_image = "zendev/impact-devimg"
    container_id = "impact_devimg_" + uuid.uuid1().hex
    pom_file = (
        env().srcroot.strpath
        + "/github.com/zenoss/impact-server/model-adapters-common/pom.xml"
    )
    command = r"sed -n 's~\s*<version>\([^<]*\)</version>~\1~p' " + pom_file
    version = subprocess.check_output(command, shell=True)
    # TODO: embedding the version number in the link means that we have to
    # rebuild the image  if the version changes.  Better if the pom.xml set
    # up a non-versioned symlink to the versioned file; then this could link
    # to the non-versioned symlink.
    startup = r"""
SRC=/mnt/src/impact-server
DST=/opt/zenoss_impact
VSN=%s
ln -fs $SRC/zenoss-dsa/target/impact-server.war $DST/webapps/impact-server.war
find $DST/lib/adapters/ -name model-adapters\*.jar | xargs rm
ln -fs $SRC/model-adapters-common/target/model-adapters-common-$VSN.jar $DST/lib/adapters
ln -fs $SRC/model-adapters-zenoss/target/model-adapters-zenoss-$VSN.jar $DST/lib/adapters/zenoss
    """ % (
        version,
    )
    with tempfile.NamedTemporaryFile() as f:
        f.write(startup)
        f.flush()
        cmd = (
            "docker run "
            "-v %s:/root/impact_devimg_init "
            "--name %s "
            "%s /bin/sh /root/impact_devimg_init"
        ) % (f.name, container_id, impact_src_image)
        subprocess.call(cmd, shell=True)
    subprocess.call(
        "docker commit %s %s" % (container_id, impact_dst_image), shell=True
    )
    subprocess.call("docker rm %s" % container_id, shell=True)


def add_commands(subparsers):
    impact_devimg_parser = subparsers.add_parser(
        "impact_devimg", help="Build a developer image for Zenoss Impact "
    )
    impact_devimg_parser.add_argument(
        "--impact-image",
        help="In an impact-devimg build, the image to use as a source to "
        "build new image on top of it",
    )

    impact_devimg_parser.set_defaults(functor=impact_devimg)
