from jinja2 import Template
import os
import string
import sys
import tempfile
from vagrantManager import VagrantManager
import subprocess
from ..log import error

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
      {% for options in shared_folders %}
      config.vm.synced_folder {{ options|join(', ') }}
      {% endfor %}
      config.vm.provision "shell", inline: "[ ! -f /vagrant/first_boot/#{vm_name} ] && source /vagrant/first_boot.sh "
    end
  end
end
""", trim_blocks=True, lstrip_blocks=True)


FIRST_BOOT = Template ("""
#! /bin/bash
# first_boot.sh file created by zendev cluster

chown zenoss:zenoss /home/zenoss/{{env_name}}
su - zenoss -c "cd /home/zenoss && zendev init {{env_name}}"

echo "
if [ -f ~/.bash_serviced ]; then
    . ~/.bash_serviced
fi" >> /home/zenoss/.bashrc
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use {{env_name}}" >> /home/zenoss/.bashrc

# We want to share etc/hosts between hosts.  Therefore we link it to a file on a mounted
# directory (/vagrant).  However, when we reboot the VM, we will need a copy of /etc/hosts
# before the /vagrant directory is mounted.  So, unmount /vagrant, copy /etc/hosts into
# /vagrant, then remount it.  Before unmounting, capture the arguments we will need to
# remount it.
MOUNT_CMD=$(awk '/^vagrant /{printf "mount -t %s -o %s %s %s", $3, $4, $1, $2}' /etc/mtab)
umount vagrant
cp /etc/hosts /vagrant/etc_hosts
$MOUNT_CMD
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

mkdir -p /vagrant/first_boot
touch /vagrant/first_boot/$(hostname)
""", trim_blocks=True, lstrip_blocks=True)


ETC_HOSTS = """
# hosts file created by zendev cluster
127.0.0.1   localhost
%s  %s 

# Shared hosts for zendev cluster
""" % (VagrantManager.VIRTUALBOX_HOST_IP, HOSTNAME)

BASH_SERVICED = """
#! /bin/bash
# .bash_serviced file created by zendev cluster
# The following list maps hosts to serviced masters.
#  To make a host a master, simply set that host's master to
#  its own IP.  (Note: %s is the IP of the vbox host.)
# serviced
eval export SERVICED_MASTER_ID=\$${HOSTNAME}_MASTER

export SERVICED_REGISTRY=1
export SERVICED_AGENT=1
export SERVICED_OUTBOUND_IP=$(ifconfig eth1 | sed -n 's/^.*inet addr:\([^ ]*\).*/\\1/p')
export SERVICED_MASTER=$( test "$SERVICED_MASTER_ID" != "$SERVICED_OUTBOUND_IP" ; echo $? )
if [ "$SERVICED_MASTER" != "1" ] ; then
    # agent only
    export SERVICED_ZK=$SERVICED_MASTER_ID:2181
    export SERVICED_ENDPOINT=$SERVICED_MASTER_ID:4979
    export SERVICED_DOCKER_REGISTRY=$SERVICED_MASTER_ID:5000
    export SERVICED_LOG_ADDRESS=$SERVICED_MASTER_ID:5042
    export SERVICED_STATS_PORT=$SERVICED_MASTER_ID:8443
    export SERVICED_LOGSTASH_ES=$SERVICED_MASTER_ID:9100
fi
""" % VagrantManager.VIRTUALBOX_HOST_IP


class VagrantClusterManager(VagrantManager):
    """
    Manages a cluster of Vagrant boxes.
    """
    def __init__(self, environment):
        super(VagrantClusterManager, self).__init__(environment, environment.clusterroot)

    def _create(self, name, purpose, count, btrfs, memory, cpus, fssize):
        self._update_hosts_allow()
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
            fssize=fssize,
            cpus=cpus,
        ))
        vagrant_dir.ensure("first_boot.sh").write(FIRST_BOOT.render(
            fses=btrfs,
            fstype="btrfs",
            env_name=self.env.name,
            hostname=VagrantManager.VIRTUALBOX_HOST_IP
        ))
        subprocess.call("ssh-keygen -f %s/id_rsa -t rsa -N ''" % vagrant_dir,
                        shell=True, stdout=subprocess.PIPE)


    def _update_hosts_allow(self):
        # Update /etc/hosts.allow to enable nfs access from vbox internal network
        hosts_allow = '/etc/hosts.allow'
        lines = [i for i in open(hosts_allow)]

        # Already updated?
        if any(line.startswith('# zendev vbox') for line in lines):
            return

        # Insert block before serviced stanza, if any.
        # serviced also edits this file, replacing all lines following
        # '# serviced, do not remove past this line'
        block = ('# zendev vbox internal network\n',
                 'rpcbind mountd nfsd statd lockd rquotad : 10.20.1.0/255.255.255.0\n',
                 '\n')
        for idx, line in enumerate(lines):
            if line.startswith('# serviced, '):
                lines[idx:idx] = block
                break
        else:
            lines.extend(block)

        print 'Updating', hosts_allow
        try:
            args = ['sudo', 'bash', '-c',
                    'cat >%s <<ZENDEV_EOF\n%s\nZENDEV_EOF' %
                    (hosts_allow, ''.join(lines))]
            subprocess.call(args)
        except Exception as err:
            print 'Failed to update %s:' % hosts_allow, err


    def ls(self, name):
        if not name:
            super(VagrantClusterManager, self).ls()
	else:
            if not self._root.join(name).exists():
                error('No cluster matching "%s" found' % name)
                sys.exit(1)
            # Each box in the cluster has its own entry under .vagrant/machines.
            for d in self._root.join(name, '.vagrant', 'machines').listdir():
                print d.basename

    def ssh(self, cluster, box):
        # We may have a box name (e.g., foo01) or a cluster name in which there is
        #  only a single box.  Check for these possibilities and disambiguate.
        if not box:
            if (len(cluster) > 2 and
                    cluster[-1] in string.digits and
                    cluster[-2] in string.digits and
                    not self._root.join(cluster).exists()):
                # Cluster not specified - infer from box
                box = cluster
                cluster = cluster[:-2]
            else:
                clusterdir = self._root.join(cluster, '.vagrant', 'machines')
                if clusterdir.exists():
                    clusterdir_contents = clusterdir.listdir()
                    if len(clusterdir_contents) == 1:
                        # Box not specified - infer from cluster
                        box = clusterdir_contents[0].basename
                    else:
                        error('Cluster "%s" has multiple boxes (%s)' %
                              (cluster, ', '.join((i.basename) for i in clusterdir_contents)))
                        sys.exit(1)
                else:
                    error('Cluster "%s" does not exist' % cluster)
                    sys.exit(1)
        super(VagrantClusterManager, self).ssh(cluster, box)


def cluster_create(args, check_env):
    env = check_env()
    env.cluster.create(args.name, args.type, args.count, args.btrfs, args.memory, args.cpus, args.fssize)
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
    env().cluster.ls(args.name)


def add_commands(subparsers):
    cluster_parser = subparsers.add_parser('cluster', help='Manage Vagrant cluster')
    cluster_subparsers = cluster_parser.add_subparsers()

    cluster_create_parser = cluster_subparsers.add_parser('create', help='Create a development vagrant cluster')
    cluster_create_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_create_parser.add_argument('--type', choices=VagrantManager.BOXES,
                                       default="ubuntu")
    cluster_create_parser.add_argument('--count', type=int, default=1)
    cluster_create_parser.add_argument('--memory', type=int, default=4096)
    cluster_create_parser.add_argument('--domain', default='zenoss.loc')
    cluster_create_parser.add_argument('--btrfs', type=int, default=0,
                                       help="Number of btrfs volumes")
    cluster_create_parser.add_argument('--cpus', type=int, default=2,
                                       help="Number of cpus")
    cluster_create_parser.add_argument('--fssize', type=int, default=24,
                                       help="Size of file system (GB)")
    cluster_create_parser.set_defaults(functor=cluster_create)

    cluster_up_parser = cluster_subparsers.add_parser('up', help='Start a vagrant cluster or node')
    cluster_up_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_up_parser.add_argument('box', nargs='?', metavar="BOX")
    cluster_up_parser.set_defaults(functor=cluster_up)

    cluster_halt_parser = cluster_subparsers.add_parser('halt', help='Stop a vagrant cluster or node')
    cluster_halt_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_halt_parser.add_argument('box', nargs ='?', metavar="BOX")
    cluster_halt_parser.set_defaults(functor=cluster_halt)

    cluster_remove_parser = cluster_subparsers.add_parser('destroy', help='Destroy a vagrant cluster')
    cluster_remove_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_remove_parser.set_defaults(functor=cluster_remove)

    cluster_ssh_parser = cluster_subparsers.add_parser('ssh', help='SSH to a node in a vagrant cluster')
    cluster_ssh_parser.add_argument('name', metavar="CLUSTER_NAME")
    cluster_ssh_parser.add_argument('box', nargs ='?', metavar="BOX")
    cluster_ssh_parser.set_defaults(functor=cluster_ssh)

    cluster_ls_parser = cluster_subparsers.add_parser('ls', help='List existing development vagrant clusters')
    cluster_ls_parser.add_argument('name', nargs='?', metavar="CLUSTER_NAME")
    cluster_ls_parser.set_defaults(functor=cluster_ls)
