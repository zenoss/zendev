from cStringIO import StringIO

import py
import vagrant
import subprocess
from jinja2 import Template

here = py.path.local(__file__).dirpath().join

VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "{{ box_name }}"
  {% for root, target in shared_folders %}
  config.vm.synced_folder "{{ root }}", "{{ target }}"
  {% endfor %}
  {% if provision_script %}
  config.vm.provision "shell", inline: <<EOF
{{ provision_script }}
EOF
  {% endif %}
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
        return vagrant.Vagrant(self._root.join(name).strpath)

    def create(self, name, purpose=CONTROLPLANE):
        if self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)
        vbox_dir = self._root.ensure(name, dir=True)
        shared = (
            (self.env.root.strpath, "/home/zenoss/" + self.env.name),
        )
        vbox_dir.ensure("Vagrantfile").write(VAGRANT.render(
            box_name=BOXES.get(purpose),
            shared_folders=shared,
            provision_script="""
            pip install git+ssh://git@github.com/zenoss/zendev.git@develop
            cd /home/zenoss && zendev init %s
            """ % self.env.name
        ))

    def remove(self, name):
        box = self._get_box(name)
        box.destroy()
        self._root.join(name).remove()

    def provision(self, name):
        provision_script = subprocess.check_output(["bash", 
            here("provision.sh").strpath])
        with self._root.join(name).as_cwd():
            proc = subprocess.Popen([vagrant.VAGRANT_EXE, "up"], 
                    stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate(provision_script)

    def ssh(self, name):
        with self._root.join(name).as_cwd():
            subprocess.call([vagrant.VAGRANT_EXE, 'ssh'])
        

