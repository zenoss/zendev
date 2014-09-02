from cStringIO import StringIO

import os
import py
import subprocess
from jinja2 import Template

from ..utils import colored, here


VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<'SCRIPT'
{{ provision_script }} 
SCRIPT

Vagrant.configure("2") do |config|
  (1..{{ box_count }}).each do |i|
    config.vm.define vm_name = "{{ cluster_name }}-%02d" % i do |config|
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
    CONTROLPLANE: "ubuntu-14.04-europa-v2",
    SOURCEBUILD: "f19-docker-zendeps",
    "ubuntu": "ubuntu-14.04-europa-v2",
    "fedora": "f19-docker-zendeps"
}

ETC_HOSTS = """
127.0.0.1    localhost

# Shared hosts for zendev cluster
"""

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

    def create(self, name, purpose=CONTROLPLANE, count=1, memory=4096):
        if not self.verify_auto_network():
            raise Exception("Unable to find or install vagrant-auto_network plugin.")
        elif self._root.join(name).check(dir=True):
            raise Exception("Vagrant box %s already exists" % name)

        vbox_dir = self._root.ensure(name, dir=True)

        vbox_dir.ensure("etc_hosts").write(ETC_HOSTS)

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
            box_name=BOXES.get(purpose),
            shared_folders=shared,
            provision_script="""
[ -e /etc/hostid ] || printf %%x $(date +%%s) > /etc/hostid

chown zenoss:zenoss /home/zenoss/%(env_name)s
su - zenoss -c "cd /home/zenoss && zendev init %(env_name)s"
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use %(env_name)s" >> /home/zenoss/.bashrc

ln -sf /vagrant/etc_hosts /etc/hosts
if ! $(grep -q ^$HOSTNAME /vagrant/etc_hosts 2>/dev/null) ; then
    IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\([^ ]*\).*/\\1/p')
    echo $HOSTNAME $IP >> /vagrant/etc_hosts
fi
""" % {'env_name':self.env.name} ))

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



def cluster_create(args, check_env):
    """
    """
    env = check_env()
    env.cluster.create(args.name, args.type, args.count, args.memory)
    env.cluster.provision(args.name, args.type)


def cluster_remove(args, env):
    env().cluster.remove(args.name)


def cluster_ssh(args, env):
    env().cluster.ssh(args.name, args.box)


def cluster_boot(args, env):
    env().cluster.boot(args.name)


def cluster_up(args, env):
    env().cluster.up(args.name, args.box)


def cluster_shutdown(args, env):
    env().cluster.shutdown(args.name)


def cluster_halt(args, env):
    env().cluster.halt(args.name, args.box)


def cluster_ls(args, env):
    env().cluster.ls()


def add_commands(subparsers):
    cluster_parser = subparsers.add_parser('cluster')
    cluster_subparsers = cluster_parser.add_subparsers()

    cluster_create_parser = cluster_subparsers.add_parser('create')
    cluster_create_parser.add_argument('name', metavar="NAME")
    cluster_create_parser.add_argument('--type', required=True, choices=BOXES)
    cluster_create_parser.add_argument('--count', type=int, default=1)
    cluster_create_parser.add_argument('--memory', type=int, default=4096)
    cluster_create_parser.add_argument('--domain', default='zenoss.loc')
    cluster_create_parser.set_defaults(functor=cluster_create)

    cluster_boot_parser = cluster_subparsers.add_parser('boot')
    cluster_boot_parser.add_argument('name', metavar="NAME")
    cluster_boot_parser.set_defaults(functor=cluster_boot)

    cluster_up_parser = cluster_subparsers.add_parser('up')
    cluster_up_parser.add_argument('name', metavar="NAME")
    cluster_up_parser.add_argument('box', metavar="BOX")
    cluster_up_parser.set_defaults(functor=cluster_up)

    cluster_shutdown_parser = cluster_subparsers.add_parser('shutdown')
    cluster_shutdown_parser.add_argument('name', metavar="NAME")
    cluster_shutdown_parser.set_defaults(functor=cluster_shutdown)

    cluster_halt_parser = cluster_subparsers.add_parser('halt')
    cluster_halt_parser.add_argument('name', metavar="NAME")
    cluster_halt_parser.add_argument('box', metavar="BOX")
    cluster_halt_parser.set_defaults(functor=cluster_halt)

    cluster_remove_parser = cluster_subparsers.add_parser('destroy')
    cluster_remove_parser.add_argument('name', metavar="NAME")
    cluster_remove_parser.set_defaults(functor=cluster_remove)

    cluster_ssh_parser = cluster_subparsers.add_parser('ssh')
    cluster_ssh_parser.add_argument('name', metavar="NAME")
    cluster_ssh_parser.add_argument('box', metavar="BOX")
    cluster_ssh_parser.set_defaults(functor=cluster_ssh)

    cluster_ls_parser = cluster_subparsers.add_parser('ls')
    cluster_ls_parser.set_defaults(functor=cluster_ls)
