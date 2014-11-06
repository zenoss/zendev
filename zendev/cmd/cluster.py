from jinja2 import Template
import os
from vagrantManager import VagrantManager

HOSTNAME=os.uname()[1]

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
if [ ! -L /etc/hosts ] ; then
    ln -sf /vagrant/etc_hosts /etc/hosts
    IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\\([^ ]*\\).*/\\1/p')
    echo $IP $HOSTNAME >> /vagrant/etc_hosts
fi
if [ ! -L /home/zenoss/.bash_serviced ] ; then
    ln -sf /vagrant/bash_serviced /home/zenoss/.bash_serviced
    sed -i "s/^\\(# serviced$\\)/${HOSTNAME}_MASTER={{hostname}}\\n\\1/" /vagrant/bash_serviced
fi

# split vdi disk into equal size partitions for each fs
fstype={{fstype}}
disk=/dev/sdb
parted $disk mktable msdos
nparts={{fses}}
incr=$(( {{fssize}} * 1024 ))
mounts=("/opt/serviced/var" "/var/lib/docker")
ii=0
while (( $ii < $nparts )); do
    di=$(($ii+1))
    parted $disk mkpart primary ext2 $(($ii*$incr)) $(($di*$incr))
    part="$disk$di"
    label="fs-$di"
    mkfs.$fstype -L $label $part
    mount=/mnt/$label
    if [[ -n ${mounts[$ii]} ]]; then
        mount=${mounts[$ii]}
    else
        mount="/mnt/$label"
    fi
    mkdir -p $mount
    echo "$part  $mount  $fstype  defaults  0  1" >>/etc/fstab
    ii=$(($ii + 1))
done
mount -a
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
        vb.customize ["modifyvm", :id, "--cpus", {{ cpus }}]{% if fses %}
        (1..1).each do |vol|
          disc_file = "mnt/#{vm_name}/{{fstype}}_#{vol}.vdi"
          unless File.exist?(disc_file)
            vb.customize ['createhd', '--filename', disc_file, '--size', {{ fses }} * {{ fssize }} * 1024]
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
%s  %s 

# Shared hosts for zendev cluster
""" % (VagrantManager.VIRTUALBOX_HOST_IP, HOSTNAME)

BASH_SERVICED = """
#! /bin/bash

# serviced
eval export SERVICED_MASTER_ID=\$${HOSTNAME}_MASTER

export SERVICED_REGISTRY=1
export SERVICED_AGENT=1
export SERVICED_MASTER=$( test "$SERVICED_MASTER_ID" != "$HOSTNAME" ; echo $? )
if [ "$SERVICED_MASTER" == "1" ] ; then
    # master only
    export SERVICED_OUTBOUND_IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\([^ ]*\).*/\\1/p')
else
    # agent only
    export SERVICED_ZK=$SERVICED_MASTER_ID:2181
    export SERVICED_ENDPOINT=$SERVICED_MASTER_ID:4979
    export SERVICED_DOCKER_REGISTRY=$SERVICED_MASTER_ID:5000
    export SERVICED_LOG_ADDRESS=$SERVICED_MASTER_ID:5042
    export SERVICED_STATS_PORT=$SERVICED_MASTER_ID:8443
    export SERVICED_LOGSTASH_ES=$SERVICED_MASTER_ID:9100
fi
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
            fses=btrfs,
            fstype="btrfs",
            fssize=24,
            cpus=4,
            env_name=self.env.name,
            hostname=HOSTNAME
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
