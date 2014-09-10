from cStringIO import StringIO

import os
import subprocess
from jinja2 import Template

from ..utils import colored, here


VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
{{ provision_script }} 
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "{{ box_name }}"
  config.vm.box_url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
  config.vm.hostname = "{{ instance_name }}"
  config.vm.network :private_network, :ip => '0.0.0.0', :auto_network => true

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", {{vm_memory}}]
    vb.customize ["modifyvm", :id, "--cpus", 4]
    {% set vdi_count = 1 %}{% for vdi in vdis %}
    vb.customize ["storageattach", :id, "--storagectl", "IDE Controller", 
                  "--port", {{ vdi_count }}, "--device", 0, "--type", "hdd", "--medium",
                  "{{ vdi }}"]{% set vdi_count = vdi_count + 1 %}{% endfor %}
  end

  {% for root, target in shared_folders %}
  config.vm.synced_folder "{{ root }}", "{{ target }}"{% endfor %}
  {% if provision_script %}config.vm.provision "shell", inline: $script{% endif %}
end
""")

PROVISION_SCRIPT = """
chown zenoss:zenoss /home/zenoss/%(env_name)s
su - zenoss -c "cd /home/zenoss && zendev init %(env_name)s"
echo "
if [ -f ~/.bash_serviced ]; then
    . ~/.bash_serviced
fi" >> /home/zenoss/.bashrc
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use %(env_name)s" >> /home/zenoss/.bashrc
%(formatDrive)s
"""

CONTROLPLANE = "controlplane"
SOURCEBUILD = "sourcebuild"

BOXES = {
    CONTROLPLANE: "ubuntu-14.04-europa-v3",
    SOURCEBUILD: "f19-docker-zendeps",
    "ubuntu": "ubuntu-14.04-europa-v3",
    "fedora": "f19-docker-zendeps"
}


def _install_auto_network():
    rc = subprocess.call(
        ["vagrant", "plugin", "install", "vagrant-auto_network"])
    if rc:
        return rc
    subprocess.call(
        "wget -qO- https://github.com/adrienthebo/vagrant-auto_network/commit/7de30cb2ce72cc8f979b8dbe5c9581646512ab1a.diff "
        "| patch -p1 -d ~/.vagrant.d/gems/gems/vagrant-auto_network*",
        shell=True)
    return 0


def verify_auto_network():
    try:
        if subprocess.call("vagrant plugin list | grep vagrant-auto_network",
                           shell=True):
            if _install_auto_network():
                return False
    except Exception:
        return False
    return True


def get_shared_directories(env):
    return (
        (env.zendev.strpath, "/home/zenoss/zendev"),
        (env.srcroot.strpath, "/home/zenoss/%s/src" % env.name),
        (env.buildroot.strpath, "/home/zenoss/%s/build" % env.name),
        (env.configroot.strpath, "/home/zenoss/%s/%s" % (env.name,
                                                         env.configroot.basename)),
    )


def make_vdis(root, relpath, btrfs):
    def make_vdi(root, relpath, diskname, size):
        with root.ensure_dir().as_cwd():
            disk = os.path.join(relpath, diskname)
            subprocess.call(
                ["VBoxManage", "createhd", "--filename", disk, "--size",
                 str(size)])
            return disk
    vdis = []
    formatDrive = []
    drive = "b"
    # Set up the btrfs volumes
    for i in range(btrfs):
        vdis.append(make_vdi(root, relpath, "btrfs_%d.vdi" % (i + 1), 24 * 1024))
        formatDrive.append(
            "mkfs.btrfs -L volume.btrfs.%d /dev/sd%s" % ((i + 1), drive))
        drive = chr(ord(drive) + 1)
    return vdis, formatDrive


class VagrantManager(object):
    """
    Manages Vagrant boxes.
    """
    def __init__(self, environment):
        self.env = environment
        self._root = self.env.vagrantroot

    def _get_box(self, name):
        import vagrant
        return vagrant.Vagrant(self._root.join(name).strpath)

    def create(self, name, purpose=CONTROLPLANE, btrfs=0, vfs=0, memory="8192"):
        if not verify_auto_network():
            raise Exception("Unable to find or install vagrant-auto_network plugin.")
        elif self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)
        vbox_dir = self._root.ensure(name, dir=True)
        shared = get_shared_directories(self.env)
        vdis, formatDrive = make_vdis(self._root.join(name), 'mnt', btrfs)
        params = dict(
            instance_name=name,
            box_name=BOXES.get(purpose),
            vdis=vdis,
            shared_folders=shared,
            vm_memory=memory,
            provision_script= PROVISION_SCRIPT % {
                'env_name': self.env.name,
                'formatDrive': "\n".join(formatDrive)
            }
        )
        vbox_dir.ensure("Vagrantfile").write(VAGRANT.render(**params))

    def up(self, name):
        box = self._get_box(name)
        box.up()

    def halt(self, name):
        box = self._get_box(name)
        box.halt()

    def remove(self, name):
        box = self._get_box(name)
        box.destroy()
        self._root.join(name).remove()

    def provision(self, name, type_):
        import vagrant
        type_ = "ubuntu" if BOXES.get(type_)==BOXES["ubuntu"] else "fedora"
        provision_script = subprocess.check_output(["bash", 
            here("provision-%s.sh" % type_).strpath])
        with self._root.join(name).as_cwd():
            proc = subprocess.Popen([vagrant.VAGRANT_EXE, "up"], 
                    stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate(provision_script)

    def ssh(self, name):
        import vagrant
        with self._root.join(name).as_cwd():
            subprocess.call([vagrant.VAGRANT_EXE, 'ssh'])

    def ls(self):
        for d in self._root.listdir(lambda p:p.join('Vagrantfile').check()):
            print "%s/%s" % (d.dirname, colored(d.basename, 'white'))


def box_create(args, check_env):
    """
    """
    env = check_env()
    env.vagrant.create(args.name, args.type, args.btrfs, args.vfs, args.memory)
    env.vagrant.provision(args.name, args.type)
    env.vagrant.ssh(args.name)


def box_remove(args, check_env):
    env = check_env()
    env.vagrant.remove(args.name)


def box_ssh(args, check_env):
    check_env().vagrant.ssh(args.name)


def box_up(args, check_env):
    check_env().vagrant.up(args.name)


def box_halt(args, check_env):
    check_env().vagrant.halt(args.name)


def box_ls(args, check_env):
    check_env().vagrant.ls()


def add_commands(subparsers):
    box_parser = subparsers.add_parser('box')
    box_subparsers = box_parser.add_subparsers()

    box_create_parser = box_subparsers.add_parser('create')
    box_create_parser.add_argument('name', metavar="NAME")
    box_create_parser.add_argument('--type', required=True, choices=BOXES)
    box_create_parser.add_argument('--btrfs', type=int, default=0,
                                   help="Number of btrfs volumes")
    box_create_parser.add_argument('--vfs', type=int, default=0)
    box_create_parser.add_argument('--memory', default="1024*8",
                                   help="memory in mb")
    box_create_parser.set_defaults(functor=box_create)

    box_up_parser = box_subparsers.add_parser('up')
    box_up_parser.add_argument('name', metavar="NAME")
    box_up_parser.set_defaults(functor=box_up)

    box_halt_parser = box_subparsers.add_parser('halt')
    box_halt_parser.add_argument('name', metavar="NAME")
    box_halt_parser.set_defaults(functor=box_halt)

    box_remove_parser = box_subparsers.add_parser('destroy')
    box_remove_parser.add_argument('name', metavar="NAME")
    box_remove_parser.set_defaults(functor=box_remove)

    box_ssh_parser = box_subparsers.add_parser('ssh')
    box_ssh_parser.add_argument('name', metavar="NAME")
    box_ssh_parser.set_defaults(functor=box_ssh)

    box_ls_parser = box_subparsers.add_parser('ls')
    box_ls_parser.set_defaults(functor=box_ls)

    ssh_parser = subparsers.add_parser('ssh')
    ssh_parser.add_argument('name', metavar="NAME")
    ssh_parser.set_defaults(functor=box_ssh)

