from cStringIO import StringIO

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
  config.vm.url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
  config.vm.hostname = "{{ instance_name }}"
  config.vm.network :private_network, ip: "10.0.5.10"
  {% for root, target in shared_folders %}
  config.vm.synced_folder "{{ root }}", "{{ target }}", :nfs => true
  {% endfor %}
  {% if provision_script %}config.vm.provision "shell", inline: $script{% endif %}
end
""")

CONTROLPLANE = "controlplane"
SOURCEBUILD = "sourcebuild"

BOXES = {
    CONTROLPLANE: "ubuntu-13.04-docker",
    SOURCEBUILD: "f19-docker-zendeps"
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

    def create(self, name, purpose=CONTROLPLANE):
        if self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)
        vbox_dir = self._root.ensure(name, dir=True)
        shared = (
            (self.env.srcroot.strpath, "/home/zenoss/%s/src" % self.env.name),
            (self.env.buildroot.strpath, "/home/zenoss/%s/build" % self.env.name),
            (self.env.configroot.strpath, "/home/zenoss/%s/%s" % (
                self.env.name, self.env.configroot.basename)),
        )
        vbox_dir.ensure("Vagrantfile").write(VAGRANT.render(
            instance_name=name,
            box_name=BOXES.get(purpose),
            shared_folders=shared,
            provision_script="""
chown zenoss:zenoss /home/zenoss/%s
su - zenoss -c "cd /home/zenoss && zendev init %s"
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use %s" >> /home/zenoss/.bashrc
""" % (self.env.name, self.env.name, self.env.name)))

    def remove(self, name):
        box = self._get_box(name)
        box.destroy()
        self._root.join(name).remove()

    def provision(self, name):
        import vagrant
        provision_script = subprocess.check_output(["bash", 
            here("provision.sh").strpath])
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
        
