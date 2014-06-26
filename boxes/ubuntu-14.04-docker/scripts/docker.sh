apt-get -y install linux-image-extra-`uname -r`

wget -qO- https://get.docker.io/gpg | apt-key add -
echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list

ufw disable

apt-get -y update
apt-get -y install lxc-docker apparmor-utils

aa-complain /usr/bin/lxc-start

usermod -a -G docker zenoss

cat  <<\EOF | sudo sed -f /dev/fd/0 -i /etc/init/docker.conf
    s/respawn/\0\nlimit nofile 65536 65536\n/
    s/DOCKER_OPTS=.*$/\0\n\tDOCKER_OPTS="$DOCKER_OPTS -dns=10.87.113.13 -dns=10.88.102.13 -dns=10.175.211.10"/
EOF
