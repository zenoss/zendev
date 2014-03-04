apt-get -y install git vim-nox emacs24-nox htop wget python-dev python-pip mercurial bzr git libpam0g-dev tmux

pip install --upgrade pip

# Download Go 1.2 and unpack it into /usr/local
wget -qO- https://go.googlecode.com/files/go1.2.1.linux-amd64.tar.gz | tar -C /usr/local -xz

# Set GOROOT and PATH appropriately
cat <<EOF > /etc/profile.d/golang.sh
    export GOROOT=/usr/local/go
    export PATH=\$GOROOT/bin:\$PATH
EOF
