from cStringIO import StringIO

import os
import py
import subprocess
from jinja2 import Template

from .utils import colored, here


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
    {% set vdi_count = 1 %}
    {% for vdi in vdis %}
    vb.customize ["storageattach", :id, "--storagectl", "SATA Controller", 
                  "--port", {{ vdi_count }}, "--device", 0, "--type", "hdd", "--medium",
                  "{{ vdi }}"]{% set vdi_count = vdi_count + 1 %}{% endfor %}
  end

  {% for root, target in shared_folders %}
  config.vm.synced_folder "{{ root }}", "{{ target }}"{% endfor %}
  {% if provision_script %}config.vm.provision "shell", inline: $script{% endif %}
end
""")

CONTROLPLANE = "controlplane"
SOURCEBUILD = "sourcebuild"

BOXES = {
    CONTROLPLANE: "ubuntu-13.04-docker-v1",
    SOURCEBUILD: "f19-docker-zendeps",
    "ubuntu": "ubuntu-13.04-docker-v1",
    "fedora": "f19-docker-zendeps"
}


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

    def _install_auto_network(self):
        rc = subprocess.call(["vagrant", "plugin", "install","vagrant-auto_network"])
        if rc:
            return rc
        subprocess.call("wget -qO- https://github.com/adrienthebo/vagrant-auto_network/commit/7de30cb2ce72cc8f979b8dbe5c9581646512ab1a.diff "
                "| patch -p1 -d ~/.vagrant.d/gems/gems/vagrant-auto_network*", shell=True)
        return 0

    def verify_auto_network(self):
        try:
            if subprocess.call("vagrant plugin list | grep vagrant-auto_network", shell=True):
                if self._install_auto_network():
                    return False
        except Exception:
            return False
        return True

    def create(self, name, purpose=CONTROLPLANE, btrfs=0, vfs=0, memory="8192"):
        if not self.verify_auto_network():
            raise Exception("Unable to find or install vagrant-auto_network plugin.")
        elif self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)

        vbox_dir = self._root.ensure(name, dir=True)
        shared = (
            (self.env.zendev.strpath, "/home/zenoss/zendev"),
            (self.env.srcroot.strpath, "/home/zenoss/%s/src" % self.env.name),
            (self.env.srcroot.strpath, "/home/zenoss/%s/src" % self.env.name),
            (self.env.buildroot.strpath, "/home/zenoss/%s/build" % self.env.name),
            (self.env.configroot.strpath, "/home/zenoss/%s/%s" % (
                self.env.name, self.env.configroot.basename)),
        )

        vdis = []
        formatDrive = []
        drive = "b"

        # Set up the btrfs volumes
        for i in range(btrfs):
            vdis.append(self.make_vdi(name, "btrfs_%d.vdi" % (i+1), 24 * 1024))
            formatDrive.append("mkfs.btrfs -L volume.btrfs.%d /dev/sd%s" % ((i+1),drive))
            drive = chr(ord(drive)+1)

        vbox_dir.ensure("Vagrantfile").write(VAGRANT.render(
            instance_name=name,
            box_name=BOXES.get(purpose),
            vdis=vdis,
            shared_folders=shared,
            vm_memory=memory,
            provision_script="""
chown zenoss:zenoss /home/zenoss/%s
su - zenoss -c "cd /home/zenoss && zendev init %s"
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use %s" >> /home/zenoss/.bashrc
%s
""" % (self.env.name, self.env.name, self.env.name, "\n".join(formatDrive))))

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

    def make_vdi(self, name, diskname, size):
        with self._root.join(name).as_cwd():
            disk = os.path.join("mnt", diskname)
            subprocess.call(["VBoxManage","createhd", "--filename", disk, "--size", str(size)])
            return disk

    def ssh(self, name):
        import vagrant
        with self._root.join(name).as_cwd():
            subprocess.call([vagrant.VAGRANT_EXE, 'ssh'])

    def ls(self):
        for d in self._root.listdir(lambda p:p.join('Vagrantfile').check()):
            print "%s/%s" % (d.dirname, colored(d.basename, 'white'))
        
