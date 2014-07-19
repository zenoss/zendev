apt-get -y install docker.io
ln -s /usr/bin/docker.io /usr/bin/docker

usermod -a -G docker zenoss

ufw disable

usermod -a -G docker zenoss

#cat  <<\EOF | sudo sed -f /dev/fd/0 -i /etc/init/docker.conf
#    s/respawn/\0\nlimit nofile 65536 65536\n/
#    s/DOCKER_OPTS=.*$/\0\n\tDOCKER_OPTS="$DOCKER_OPTS -dns=10.87.113.13 -dns=10.88.102.13 -dns=10.175.211.10"/
#EOF
