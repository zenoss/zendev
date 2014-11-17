from jinja2 import Template

from vagrantManager import VagrantManager

VAGRANT = Template("""
# -*- mode: ruby -*-
# vi: set ft=ruby :
# Vagrantfile created by zendev box

$script = <<SCRIPT
chown zenoss:zenoss /home/zenoss/{{env_name}}
su - zenoss -c "cd /home/zenoss && zendev init {{env_name}}"
echo "
if [ -f ~/.bash_serviced ]; then
    . ~/.bash_serviced
fi" >> /home/zenoss/.bashrc
echo "source $(zendev bootstrap)" >> /home/zenoss/.bashrc
echo "zendev use {{env_name}}" >> /home/zenoss/.bashrc
{%for i in range(vdis) %}
{{"mkfs.btrfs -L volume.btrfs.%d /dev/sd%s"|format(i+1, "bcdef"[i])}} {%endfor%}
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.box = "{{ box_name }}"
  config.vm.box_url = "http://vagrant.zendev.org/boxes/{{ box_name }}.box"
  config.vm.hostname = "{{ instance_name }}"
  config.vm.network :private_network, :ip => '0.0.0.0', :auto_network => true

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", {{vm_memory}}]
    vb.customize ["modifyvm", :id, "--cpus", 4] {% if vdis %}
    (1..{{ vdis }}).each do |vol|
      disc_file = "mnt/btrfs_#{vol}.vdi"
      unless File.exist?(disc_file)
        vb.customize ['createhd', '--filename', disc_file, '--size', 24 * 1024]
      end
      vb.customize ["storageattach", :id, "--storagectl", "IDE Controller",
                    "--port", vol, "--device", 0, "--type", "hdd", "--medium",
                    disc_file ]
    end{% endif %}
  end
  {% for root, target in shared_folders %}
  config.vm.synced_folder "{{ root }}", "{{ target }}"{% endfor %}
  config.vm.provision "shell", inline: $script
end

""")


class VagrantBoxManager(VagrantManager):
    def __init__(self, environment):
        super(VagrantBoxManager, self).__init__(environment, environment.vagrantroot)

    def _create(self, name, purpose, btrfs, vfs, memory):
        self._root.ensure_dir(name).ensure("Vagrantfile").write(VAGRANT.render(
            instance_name=name,
            box_name=VagrantManager.BOXES.get(purpose),
            vdis=btrfs,
            shared_folders=self.get_shared_directories(),
            vm_memory=memory,
            env_name=self.env.name
        ))


def box_create(args, check_env):
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
    box_create_parser.add_argument('--type', choices=VagrantManager.BOXES,
                                   default="ubuntu")
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

