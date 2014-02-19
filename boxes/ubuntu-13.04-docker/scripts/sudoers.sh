#!/bin/bash -eux

sed -i -e '/Defaults\s\+env_reset/a Defaults\texempt_group=admin' /etc/sudoers
sed -i -e 's/%admin ALL=(ALL) ALL/%admin ALL=NOPASSWD:ALL/g' /etc/sudoers
echo 'Defaults:zenoss !requiretty' > /etc/sudoers.d/zenoss
echo "zenoss        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers.d/zenoss
chmod 0440 /etc/sudoers.d/zenoss
