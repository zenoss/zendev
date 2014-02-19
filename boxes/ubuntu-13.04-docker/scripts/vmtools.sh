#!/bin/bash

if [ $PACKER_BUILDER_TYPE == 'virtualbox' ]; then
    mkdir /tmp/vbox
    VER=$(cat /home/zenoss/.vbox_version)
    mount -o loop /home/zenoss/VBoxGuestAdditions_$VER.iso /tmp/vbox 
    sh /tmp/vbox/VBoxLinuxAdditions.run
    umount /tmp/vbox
    rmdir /tmp/vbox
    rm /home/zenoss/*.iso
fi

if [ $PACKER_BUILDER_TYPE == 'vmware' ]; then
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
