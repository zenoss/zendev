#!/bin/bash -eux
apt-get remove -y build-essential
apt-get -y autoremove
apt-get -y clean
rm -rf VBoxGuestAdditions_*.iso VBoxGuestAdditions_*.iso.?
rm -rf /tmp/*


rm -f /home/zenoss/*.sh
rm -f /home/zenoss/*.gz
rm -f /home/zenoss/*.iso
rm -f /home/zenoss/_*
