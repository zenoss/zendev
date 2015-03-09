import subprocess
from ..utils import colored, here


class VagrantManager(object):
    """
    Manages Vagrant boxes.
    """
    CONTROLPLANE = "controlplane"
    SOURCEBUILD = "sourcebuild"

    BOXES = {
        CONTROLPLANE: "ubuntu-14.04-europa-v4",
        SOURCEBUILD: "f19-docker-zendeps",
        "ubuntu": "ubuntu-14.04-europa-v4",
        "fedora": "f19-docker-zendeps"
    }

    # The IP of the virtualbox host, as set by vagrant-auto_network plugin.
    VIRTUALBOX_HOST_IP = "10.20.1.1"

    def __init__(self, environment, root):
        self.env = environment
        self._root = root

    def create(self, name, *args, **kwargs):
        if not self._verify_auto_network():
            raise Exception("Unable to find or install vagrant-auto_network plugin.")
        elif self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)
        self._root.ensure_dir(name)
        self._create(name, *args, **kwargs)

    def _install_auto_network(self):
        rc = subprocess.call(
            ["vagrant", "plugin", "install", "vagrant-auto_network"])
        if rc:
            return rc
        subprocess.call(
            "wget -qO- https://github.com/adrienthebo/vagrant-auto_network/commit/7de30cb2ce72cc8f979b8dbe5c9581646512ab1a.diff "
            "| patch -p1 -d ~/.vagrant.d/gems/gems/vagrant-auto_network*",
            shell=True)
        return 0

    def _verify_auto_network(self):
        try:
            if subprocess.call("vagrant plugin list | grep vagrant-auto_network",
                               shell=True):
                if self._install_auto_network():
                    return False
        except Exception:
            return False
        return True

    def get_shared_directories(self):
        env=self.env
        return (
            ('"%s"' % env.zendev.strpath, '"/home/zenoss/zendev"'),
            ('"%s"' % env.srcroot.strpath, '"/home/zenoss/%s/src"' % env.name),
            ('"%s"' % env.buildroot.strpath, '"/home/zenoss/%s/build"' % env.name),
            ('"%s"' % env.var_zenoss.strpath, '"/home/zenoss/%s/var_zenoss"' % env.name),
            ('"%s"' % env.zenhome.strpath, '"/home/zenoss/%s/zenhome"' % env.name,
                "type: 'nfs'",
                ":linux__nfs_options => ['rw,no_root_squash,no_subtree_check']"),
            ('"%s"' % env.configroot.strpath, '"/home/zenoss/%s/%s"' %
                                     (env.name, env.configroot.basename)) )

    def _get_box(self, name):
        import vagrant
        return vagrant.Vagrant(self._root.join(name).strpath)

    def up(self, name, box=None):
        vagrant = self._get_box(name)
        vagrant.up(vm_name=box)

    def halt(self, name, box=None):
        vagrant = self._get_box(name)
        vagrant.halt(vm_name=box)

    def remove(self, name):
        vagrant = self._get_box(name)
        vagrant.destroy()
        self._root.join(name).remove()

    def provision(self, name, type_):
        import vagrant
        BOXES=VagrantManager.BOXES
        type_ = "ubuntu" if BOXES.get(type_)==BOXES["ubuntu"] else "fedora"
        provision_script = subprocess.check_output(["bash",
            here("provision-%s.sh" % type_).strpath])
        with self._root.join(name).as_cwd():
            proc = subprocess.Popen([vagrant.VAGRANT_EXE, "up"],
                    stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate(provision_script)

    def ssh(self, name, box=None):
        import vagrant
        with self._root.join(name).as_cwd():
            subprocess.call([vagrant.VAGRANT_EXE, 'ssh'] + ([box] if box else []))

    def ls(self):
        for d in self.get_boxes():
            print "%s/%s" % (d.dirname, colored(d.basename, 'white'))

    def get_boxes(self):
        for d in self._root.listdir(lambda p:p.join('Vagrantfile').check()):
            yield d
