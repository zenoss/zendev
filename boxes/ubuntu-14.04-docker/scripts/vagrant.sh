#!/bin/bash

mkdir /home/zenoss/.ssh
wget --no-check-certificate \
    'https://github.com/mitchellh/vagrant/raw/master/keys/vagrant.pub' \
    -O /home/zenoss/.ssh/authorized_keys
chown -R zenoss /home/zenoss/.ssh
chmod -R go-rwsx /home/zenoss/.ssh

mkdir -p /root/.ssh
cp /home/zenoss/.ssh/authorized_keys /root/.ssh/authorized_keys
chown -R root:root /root/.ssh
chmod -R go-rwsx /root/.ssh

date > /etc/vagrant_box_build_time
