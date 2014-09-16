from jinja2 import Template

from vagrantManager import VagrantManager


VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :
# Vagrantfile created by zendev cluster

$script = <<'SCRIPT'
chown zenoss:zenoss /home/zenoss/{{env_name}}
su - zenoss -c "cd /home/zenoss && zendev init {{env_name}}"
echo "
if [ -f ~/.bash_serviced ]; then
    . ~/.bash_serviced
fi" >> /home/zenoss/.bashrc
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use {{env_name}}" >> /home/zenoss/.bashrc
[ -e /etc/hostid ] || printf %x $(date +%s) > /etc/hostid
ln -sf /vagrant/etc_hosts /etc/hosts
if ! $(grep -q ^$HOSTNAME /vagrant/etc_hosts 2>/dev/null) ; then
    IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\\([^ ]*\\).*/\\1/p')
    echo $IP $HOSTNAME >> /vagrant/etc_hosts
fi
ln -sf /vagrant/bash_serviced /home/zenoss/.bash_serviced
if ! $(grep -q ^${HOSTNAME}_MASTER /vagrant/bash_serviced 2>/dev/null) ; then
    sed -i "s/^\\(# serviced$\\)/${HOSTNAME}_MASTER=vb_host\\n\\1/" /vagrant/bash_serviced
fi
{%for i in range(vdis) %}
{{"mkfs.btrfs -L volume.btrfs.%d /dev/sd%s"|format(i+1, "bcdef"[i])}} {%endfor%}
SCRIPT

Vagrant.configure("2") do |config|
  (1..{{ box_count }}).each do |box|
    config.vm.define vm_name = "{{ cluster_name }}%02d" % box do |config|
      config.vm.box = "{{ box_name }}"
      config.vm.box_url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
      config.vm.network :private_network, :ip => '0.0.0.0', :auto_network => true
      config.vm.hostname = vm_name
      config.vm.provider :virtualbox do |vb|
        vb.customize ["modifyvm", :id, "--memory", "{{ box_memory }}"]
        vb.customize ["modifyvm", :id, "--cpus", 4]{% if vdis %}
        (1..{{ vdis }}).each do |vol|
          disc_file = "mnt/#{vm_name}/btrfs_#{vol}.vdi"
          unless File.exist?(disc_file)
            vb.customize ['createhd', '--filename', disc_file, '--size', 24 * 1024]
          end
          vb.customize ["storageattach", :id, "--storagectl", "IDE Controller",
                        "--port", vol, "--device", 0, "--type", "hdd", "--medium",
                        disc_file ]
        end{% endif %}
      end{% for root, target in shared_folders %}
      config.vm.synced_folder "{{ root }}", "{{ target }}"{% endfor %}
      config.vm.provision "shell", inline: $script
    end
  end
end

""")



ETC_HOSTS = """
127.0.0.1   localhost
%s   vb_host

# Shared hosts for zendev cluster
""" % VagrantManager.VIRTUALBOX_HOST_IP

BASH_SERVICED = """
#! /bin/bash

# serviced
eval export MASTER=\$${HOSTNAME}_MASTER
export SERVICED_DOCKER_REGISTRY=$MASTER:5000
export SERVICED_STATS_PORT=$MASTER:8442
export SERVICED_ENDPOINT=$MASTER:4979
export SERVICED_LOG_ADDRESS=$MASTER:5042
export SERVICED_OUTBOUND_IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\([^ ]*\).*/\\1/p')
export SERVICED_REGISTRY=1
"""

class VagrantClusterManager(VagrantManager):
    """
    Manages a cluster of Vagrant boxes.
    """
    def __init__(self, environment):
        super(VagrantClusterManager, self).__init__(environment, environment.clusterroot)

    def _create(self, name, purpose, count, btrfs, memory):
        vagrant_dir = self._root.ensure_dir(name)
        vagrant_dir.ensure("etc_hosts").write(ETC_HOSTS)
        vagrant_dir.ensure("bash_serviced").write(BASH_SERVICED)
        vagrant_dir.ensure("Vagrantfile").write(VAGRANT.render(
            cluster_name=name,
            box_count=count,
            box_memory=memory,
            box_name=VagrantManager.BOXES.get(purpose),
            shared_folders=self.get_shared_directories(),
            vdis=btrfs,
            env_name=self.env.name,
        ))


def cluster_create(args, check_env):
    env = check_env()
    env.cluster.create(args.name, args.type, args.count, args.btrfs, args.memory)
    env.cluster.provision(args.name, args.type)


def cluster_remove(args, env):
    env().cluster.remove(args.name)


def cluster_ssh(args, env):
    env().cluster.ssh(args.name, args.box)


def cluster_boot(args, env):
    env().cluster.up(args.name)


def cluster_up(args, env):
    env().cluster.up(args.name, args.box)


def cluster_shutdown(args, env):
    env().cluster.halt(args.name)


def cluster_halt(args, env):
    env().cluster.halt(args.name, args.box)


def cluster_ls(args, env):
    env().cluster.ls()


def add_commands(subparsers):
    cluster_parser = subparsers.add_parser('cluster')
    cluster_subparsers = cluster_parser.add_subparsers()

    cluster_create_parser = cluster_subparsers.add_parser('create')
    cluster_create_parser.add_argument('name', metavar="NAME")
    cluster_create_parser.add_argument('--type', choices=VagrantManager.BOXES,
                                       default="ubuntu")
    cluster_create_parser.add_argument('--count', type=int, default=1)
    cluster_create_parser.add_argument('--memory', type=int, default=4096)
    cluster_create_parser.add_argument('--domain', default='zenoss.loc')
    cluster_create_parser.add_argument('--btrfs', type=int, default=0,
                                   help="Number of btrfs volumes")
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
