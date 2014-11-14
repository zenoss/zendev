from jinja2 import Template
import os
from vagrantManager import VagrantManager
import subprocess

HOSTNAME=os.uname()[1]

VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :
# Vagrantfile created by zendev cluster

Vagrant.configure("2") do |config|
  (1..{{ box_count }}).each do |box|
    config.vm.define vm_name = "{{ cluster_name }}%02d" % box do |config|
      config.vm.box = "{{ box_name }}"
      config.vm.box_url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
      config.vm.network :private_network, :ip => '0.0.0.0', :auto_network => true
      config.vm.hostname = vm_name
      config.vm.provider :virtualbox do |vb|
        vb.customize ["modifyvm", :id, "--memory", "{{ box_memory }}"]
        vb.customize ["modifyvm", :id, "--cpus", {{ cpus }}]
        {% if fses %}
        disc_dir = "mnt/#{vm_name}"
        unless File.exist?(disc_dir)
          vb.customize ["storagectl", :id, "--name", "SATA", "--add", "sata", "--controller", "IntelAhci",
                       "--portcount", {{fses}}, "--hostiocache", "on", "--bootable", "off"]
        end
        (1..{{fses}}).each do |vol|
          disc_file = "#{disc_dir}/{{fstype}}_#{vol}.vdi"
          unless File.exist?(disc_file)
            vb.customize ['createhd', '--filename', disc_file, '--size', {{ fssize }} * 1024]
          end
          vb.customize ["storageattach", :id, "--storagectl", "SATA",
                        "--port", vol, "--device", 0, "--type", "hdd", "--medium",
                        disc_file ]
        end
        {% endif %}
      end
      {% for root, target in shared_folders %}
      config.vm.synced_folder "{{ root }}", "{{ target }}"
      {% endfor %}
      config.vm.provision "shell", inline: "[ ! -f /vagrant/first_boot.sh ] || source /vagrant/first_boot.sh "
    end
  end
end
""", trim_blocks=True, lstrip_blocks=True)


FIRST_BOOT = Template ("""
#! /bin/bash
# init.sh file created by zendev cluster

chown zenoss:zenoss /home/zenoss/{{env_name}}
su - zenoss -c "cd /home/zenoss && zendev init {{env_name}}"

echo "
if [ -f ~/.bash_serviced ]; then
    . ~/.bash_serviced
fi" >> /home/zenoss/.bashrc
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use {{env_name}}" >> /home/zenoss/.bashrc

printf %x $(date +%s) > /etc/hostid

ln -sf /vagrant/etc_hosts /etc/hosts
IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\\([^ ]*\\).*/\\1/p')
echo $IP $HOSTNAME >> /vagrant/etc_hosts

ln -sf /vagrant/bash_serviced /home/zenoss/.bash_serviced
sed -i "s/^\\(# serviced$\\)/${HOSTNAME}_MASTER={{hostname}}\\n\\1/" /vagrant/bash_serviced
ln -sf /vagrant/id_rsa /home/zenoss/.ssh/id_rsa

ln -sf /vagrant/id_rsa.pub /home/zenoss/.ssh/id_rsa.pub
cat /home/zenoss/.ssh/id_rsa.pub >> /home/zenoss/.ssh/authorized_keys

{% if fses -%}
    # create a filesystem on each added disk
    {%set letters = "bcdefghijklmnopqrstuvwxyz"%}
    {%set mountpoints = ["/var/lib/docker", "/opt/serviced/var"] %}
    {%for i in range(fses) %}
        {%set devname = "sd%s"|format(letters[i])%}
        {%set device = "/dev/%s"|format(devname)%}
        {%if mountpoints|length > i %}
            {%set mountpoint = mountpoints[i]%}
        {%else%}
            {%set mountpoint = "/mnt/fs-%s"|format(devname)%}
        {%endif%}
        {{- "mkfs.%s -L fs-%s %s\n"|format(fstype, devname, device)}}
        {{- "mkdir -p %s\n"|format(mountpoint)}}
        {{- "echo '%s  %s  %s  defaults  0  1' >>/etc/fstab"|format(device, mountpoint, fstype)}}
    {%endfor%}
    {{- "mount -a"}}
{%endif%}

mv /vagrant/first_boot.sh /vagrant/first_boot.sh.orig
""", trim_blocks=True, lstrip_blocks=True)


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
        ))
        vagrant_dir.ensure("first_boot.sh").write(FIRST_BOOT.render(
            fses=btrfs,
            fstype="btrfs",
            env_name=self.env.name,
            hostname=HOSTNAME
        ))
        subprocess.call("ssh-keygen -f %s/id_rsa -t rsa -N ''" % vagrant_dir, shell=True,
                        stdout=subprocess.PIPE)


def cluster_create(args, check_env):
    env = check_env()
    env.cluster.create(args.name, args.type, args.count, args.btrfs, args.memory)
    env.cluster.provision(args.name, args.type)


def cluster_remove(args, env):
    env().cluster.remove(args.name)


def cluster_ssh(args, env):
    env().cluster.ssh(args.name, args.box)


def cluster_up(args, env):
    env().cluster.up(args.name, args.box)


def cluster_halt(args, env):
    env().cluster.halt(args.name, args.box)


def cluster_ls(args, env):
    env().cluster.ls()


def add_commands(subparsers):
    cluster_parser = subparsers.add_parser('cluster')
    cluster_subparsers = cluster_parser.add_subparsers()

    cluster_create_parser = cluster_subparsers.add_parser('create')
    cluster_create_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_create_parser.add_argument('--type', choices=VagrantManager.BOXES,
                                       default="ubuntu")
    cluster_create_parser.add_argument('--count', type=int, default=1)
    cluster_create_parser.add_argument('--memory', type=int, default=4096)
    cluster_create_parser.add_argument('--domain', default='zenoss.loc')
    cluster_create_parser.add_argument('--btrfs', type=int, default=0,
                                   help="Number of btrfs volumes")
    cluster_create_parser.set_defaults(functor=cluster_create)

    cluster_up_parser = cluster_subparsers.add_parser('up')
    cluster_up_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_up_parser.add_argument('box', nargs='?', metavar="BOX")
    cluster_up_parser.set_defaults(functor=cluster_up)

    cluster_halt_parser = cluster_subparsers.add_parser('halt')
    cluster_halt_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_halt_parser.add_argument('box', nargs ='?', metavar="BOX")
    cluster_halt_parser.set_defaults(functor=cluster_halt)

    cluster_remove_parser = cluster_subparsers.add_parser('destroy')
    cluster_remove_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_remove_parser.set_defaults(functor=cluster_remove)

    cluster_ssh_parser = cluster_subparsers.add_parser('ssh')
    cluster_ssh_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_ssh_parser.add_argument('box', metavar="BOX")
    cluster_ssh_parser.set_defaults(functor=cluster_ssh)

    cluster_ls_parser = cluster_subparsers.add_parser('ls')
    cluster_ls_parser.set_defaults(functor=cluster_ls)
