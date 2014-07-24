apt-get -y install    \
    git               \
    vim-nox           \
    emacs24-nox       \
    htop              \
    wget              \
    python-dev        \
    python-pip        \
    mercurial         \
    bzr               \
    libpam0g-dev      \
    tmux              \
    screen            \
    curl              \
    btrfs-tools       \
    nfs-common        \
    nfs-kernel-server \
    net-tools         \
    libncurses5-dev   \
    golang

wget https://www.kernel.org/pub/linux/utils/util-linux/v2.24/util-linux-2.24.tar.bz2
bzip2 -d -c util-linux-2.24.tar.bz2 | tar xf -
cd util-linux-2.24/
./configure --without-ncurses --prefix=/usr/local/util-linux
make
make install
cp -p /usr/local/util-linux/bin/nsenter /usr/local/bin

pip install --upgrade pip
