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
  (1..{{ box_count }}).each do |i|
    config.vm.define vm_name = "{{ cluster_name }}-%02d.{{ cluster_domain }}" % i do |config|
      config.vm.box = "{{ box_name }}"
      config.vm.box_url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
      config.vm.network :private_network, :ip => '0.0.0.0', :auto_network => true

      config.vm.hostname = vm_name

      config.vm.provider :virtualbox do |vb|
        vb.customize ["modifyvm", :id, "--memory", "{{ box_memory }}"]
        vb.customize ["modifyvm", :id, "--cpus", 4]
      end

      {% for root, target in shared_folders %}
      config.vm.synced_folder "{{ root }}", "{{ target }}"{% endfor %}
      {% if provision_script %}config.vm.provision "shell", inline: $script{% endif %}
    end
  end
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


class VagrantClusterManager(object):
    """
    Manages a cluster of Vagrant boxes.
    """
    def __init__(self, environment):
        self.env = environment
        self._root = self.env.clusterroot

    def _get_cluster(self, name):
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

    def create(self, name, purpose=CONTROLPLANE, count=1, domain="zenoss.loc", memory=4096):
        if not self.verify_auto_network():
            raise Exception("Unable to find or install vagrant-auto_network plugin.")
        elif self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)

        vbox_dir = self._root.ensure(name, dir=True)
        shared = (
            (self.env.zendev.strpath, "/home/zenoss/zendev"),
            (self.env.srcroot.strpath, "/home/zenoss/%s/src" % self.env.name),
            (self.env.buildroot.strpath, "/home/zenoss/%s/build" % self.env.name),
            (self.env.configroot.strpath, "/home/zenoss/%s/%s" % (
                self.env.name, self.env.configroot.basename)),
        )

        vbox_dir.ensure("Vagrantfile").write(VAGRANT.render(
            cluster_name=name,
            box_count=count,
            box_memory=memory,
            cluster_domain=domain,
            box_name=BOXES.get(purpose),
            shared_folders=shared,
            provision_script="""
chown zenoss:zenoss /home/zenoss/%s
su - zenoss -c "cd /home/zenoss && zendev init %s"
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use %s" >> /home/zenoss/.bashrc
""" % (self.env.name, self.env.name, self.env.name)))

    def boot(self, name):
        cluster = self._get_cluster(name)
        cluster.up()

    def up(self, name, box):
        cluster = self._get_cluster(name)
        cluster.up(vm_name=box)

    def shutdown(self, name):
        cluster = self._get_cluster(name)
        cluster.halt()

    def halt(self, name, box):
        cluster = self._get_cluster(name)
        cluster.halt(vm_name=box)

    def remove(self, name):
        cluster = self._get_cluster(name)
        cluster.destroy()
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

    def ssh(self, name, box):
        import vagrant
        with self._root.join(name).as_cwd():
            subprocess.call([vagrant.VAGRANT_EXE, 'ssh', box])

    def ls(self):
        for d in self._root.listdir(lambda p:p.join('Vagrantfile').check()):
            print "%s/%s" % (d.dirname, colored(d.basename, 'white'))
