apt-get -y install linux-image-extra-`uname -r`

wget -qO- https://get.docker.io/gpg | apt-key add -
echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list

ufw disable

apt-get -y update
apt-get -y install lxc-docker-0.8.1

usermod -a -G docker zenoss

cat <<EOF > /etc/init/docker.conf
description "Docker daemon"

start on filesystem and started lxc-net
stop on runlevel [!2345]

respawn

limit nofile 65536 65536

script
        DOCKER=/usr/bin/\$UPSTART_JOB
        DOCKER_OPTS="-dns=10.87.110.13 -dns=10.87.113.13 -dns=10.88.102.13"
        if [ -f /etc/default/\$UPSTART_JOB ]; then
                . /etc/default/\$UPSTART_JOB
        fi
        "\$DOCKER" -d \$DOCKER_OPTS
end script
EOF
