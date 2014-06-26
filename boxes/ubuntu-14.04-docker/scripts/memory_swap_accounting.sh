# Enable memory cgroup and swap accounting for Docker.
# http://docs.docker.com/installation/ubuntulinux/#memory-and-swap-accounting
set -ex
sed -i 's/^GRUB_CMDLINE_LINUX=""$/GRUB_CMDLINE_LINUX="cgroup_enable=memory swapaccount=1"/' /etc/default/grub
update-grub
