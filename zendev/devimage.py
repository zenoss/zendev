import os
import subprocess


class DevImage(object):
    """
    Represents an instance of zendev/devimg.
    """
    def __init__(self, env):
        self.env = env

    def get_image_name(self):
        zenoss_image = 'zendev/devimg:' + self.env.name
        image_id = subprocess.check_output(['docker', 'images', '-q', zenoss_image])
        if image_id:
            return zenoss_image
        return 'zendev/devimg:latest'

    def image_exists(self, imageName):
        """
        return the image repo/tag for devimg
        prefer the image for this environment if one exists; otherwise the latest
        exit the program with a warning if no image is available
        """
        if subprocess.check_output(['docker', 'images', '-q', imageName]) != '':
            return True
        return False

    def get_mounts(self):
        """
        return a map of mount points in the form of
        OS-local-directory-name:container-local-directory-name
        """
        envvars = self.env.envvars()
        envvars['HOME'] = os.getenv('HOME')
        mounts = {
            os.path.join(envvars["HOME"], ".m2"):           "/home/zenoss/.m2",
            self.env.root.join("zenhome").strpath:               "/opt/zenoss",
            self.env.var_zenoss.strpath:                         "/var/zenoss",
            self.env.root.join("src/github.com/zenoss").strpath: "/mnt/src"
        }
        return mounts

