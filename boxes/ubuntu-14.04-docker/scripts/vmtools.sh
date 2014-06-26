#!/bin/bash

if [ $PACKER_BUILDER_TYPE == 'virtualbox-iso' ]; then
    set -ex
    apt-get -y install --no-install-recommends libdbus-1-3
    set +e
    /etc/init.d/virtualbox-guest-utils stop
    /etc/init.d/virtualbox-guest-x11 stop
    rmmod vboxguest
    set -e
    apt-get -y purge virtualbox-guest-x11 virtualbox-guest-dkms virtualbox-guest-utils
    apt-get -y install dkms
    mkdir /tmp/vbox
    VER=$(cat /home/zenoss/.vbox_version)
    mount -o loop /home/zenoss/VBoxGuestAdditions_$VER.iso /tmp/vbox 
    set +e
    yes|sh /tmp/vbox/VBoxLinuxAdditions.run -- install /VBoxLinuxAdditions
    set -e
    umount /tmp/vbox
    if [[ ! -e /usr/lib/VBoxGuestAdditions ]]; then
      ln -s /VBoxLinuxAdditions/lib/VBoxGuestAdditions /usr/lib/VBoxGuestAdditions
    fi
    /etc/init.d/vboxadd start
    lsmod | grep -q vboxguest
    rmdir /tmp/vbox
    rm /home/zenoss/*.iso
fi

if [ $PACKER_BUILDER_TYPE == 'vmware-iso' ]; then
    mkdir /tmp/vmfusion
    mkdir /tmp/vmfusion-archive
    mount -o loop /home/zenoss/linux.iso /tmp/vmfusion
    tar xzf /tmp/vmfusion/VMwareTools-*.tar.gz -C /tmp/vmfusion-archive
    /tmp/vmfusion-archive/vmware-tools-distrib/vmware-install.pl --default
    umount /tmp/vmfusion
    rm -rf  /tmp/vmfusion
    rm -rf  /tmp/vmfusion-archive
    rm /home/zenoss/*.iso
fi
