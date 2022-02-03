from __future__ import absolute_import, print_function

import os
import subprocess


class DevImage(object):
    """
    Represents an instance of zendev/devimg.
    """

    def __init__(self, env):
        self.env = env

    def get_image_name(self):
        image = self._get_name("devimg")
        return image if image else "zendev/devimg:latest"

    def get_mariadb_name(self):
        return self._get_name("mariadb")

    def _get_name(self, basename):
        image_name = "zendev/{base}:{tag}".format(
            base=basename,
            tag=self.env.name,
        )
        image_id = subprocess.check_output(
            ["docker", "images", "-q", image_name]
        )
        return image_name if image_id else None

    def image_exists(self, imageName):
        """Return True if the given image name exists.

        Returns False if the image name is not found.
        """
        if imageName is None:
            return False
        cmd = ["docker", "images", "-q", imageName]
        return subprocess.check_output(cmd) != ""

    def get_mounts(self):
        """
        return a map of mount points in the form of
        OS-local-directory-name:container-local-directory-name
        """
        envvars = self.env.envvars()
        envvars["HOME"] = os.getenv("HOME")
        mounts = {
            os.path.join(envvars["HOME"], ".m2"): "/home/zenoss/.m2",
            self.env.root.join("zenhome").strpath: "/opt/zenoss",
            self.env.var_zenoss.strpath: "/var/zenoss",
            self.env.root.join("src/github.com/zenoss").strpath: "/mnt/src",
        }
        return mounts
