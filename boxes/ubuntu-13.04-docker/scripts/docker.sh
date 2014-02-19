apt-get -y install linux-image-extra-`uname -r`

wget -qO- https://get.docker.io/gpg | apt-key add -
echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list

ufw disable

apt-get -y update
apt-get -y install lxc-docker-0.7.6

usermod -a -G docker zenoss
