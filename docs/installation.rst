============
Installation
============

Other things being equal, Zenoss development as a whole is easiest on Ubuntu.
That said, zendev can work on any platform that isn't Windows, and includes an
Ubuntu Vagrant box already set up with the proper dependencies.

Here's how to set up a full Zenoss development environment on Ubuntu (in case
you were wondering, these instructions go far beyond the requirements for
zendev itself, which are basically git and Python).

Ubuntu
------
.. important:: Ubuntu 13.04 or higher is required.

1. Make sure the universe and multiverse repos are enabled and updated:

.. code-block:: bash

    # Add the repository
    sudo add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) main universe restricted multiverse"

    # Update the repos
    sudo apt-get update

2. Install Docker_ (`source <http://docs.docker.io/en/latest/installation/ubuntulinux/#ubuntu-raring-saucy>`_):

.. code-block:: bash

    # Make sure AUFS is installed
    sudo apt-get install -y linux-image-extra-`uname -r`

    # Add the repository key
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9

    # Add the Docker repository
    sudo sh -c "echo deb http://get.docker.io/ubuntu docker main\
        > /etc/apt/sources.list.d/docker.list"

    # Install Docker
    sudo apt-get update && sudo apt-get install -y lxc-docker-0.8.1 apparmor-utils

3. Add your user to the ``docker`` group:

.. code-block:: bash

    # Add the current user to the docker group
    sudo usermod -a -G docker ${USER}

    # Login again to get docker group (requires password reentry)
    exec su -l ${USER}

    # Allow lxc-start to start (see https://github.com/dotcloud/docker/issues/2702)
    sudo /usr/sbin/aa-complain /usr/bin/lxc-start

    # Restart Docker
    sudo service docker restart

Test that you can communicate with the docker daemon:

.. code-block:: bash

    docker ps

If you see an empty list of containers (i.e., a row of column names), you're
good. Now modify the Docker upstart script to handle resolution of local DNS:

.. code-block:: bash

    cat  <<\EOF | sudo sed -f /dev/fd/0 -i /etc/init/docker.conf
        s/respawn/\0\nlimit nofile 65536 65536\n/
        s/DOCKER_OPTS=.*$/\0\n\tDOCKER_OPTS="$DOCKER_OPTS -dns=10.87.113.13 -dns=10.88.102.13 -dns=10.175.211.10"/
    EOF


5. Install Go_:

.. code-block:: bash

    # Install "go get" dependencies.
    sudo apt-get install -y mercurial bzr git

    # Download Go 1.2.1 and unpack it into /usr/local
    sudo apt-get install -y wget
    wget -qO- https://go.googlecode.com/files/go1.2.1.linux-amd64.tar.gz | sudo tar -C /usr/local -xz

    # Set GOROOT and PATH appropriately
    cat <<\EOF | sudo bash -c "cat > /etc/profile.d/golang.sh"
        export GOROOT=/usr/local/go
        export PATH=$GOROOT/bin:$PATH
    EOF

    # Source the new profile
    source /etc/profile.d/golang.sh

    # Add important/useful golang things
    export GOPATH=/opt/go

    sudo mkdir -p ${GOPATH}/{bin,pkg,src}
    sudo chown -R ${USER}:${USER} ${GOPATH}

    go get github.com/golang/lint/golint
    sudo ln -s ${GOPATH}/bin/golint /usr/local/bin/golint

    go get -v code.google.com/p/rog-go/exp/cmd/godef
    go install -v code.google.com/p/rog-go/exp/cmd/godef
    sudo ln -s ${GOPATH}/bin/godef /usr/local/bin/godef

    go get -u github.com/nsf/gocode
    sudo ln -s ${GOPATH}/bin/gocode /usr/local/bin/gocode

    go get code.google.com/p/go.tools/cmd/goimports
    sudo ln -s ${GOPATH}/bin/goimports /usr/local/bin/goimports

6. Install other dependencies:

.. code-block:: bash

    # Python, pip
    sudo apt-get install -y python-dev python-pip
    sudo pip install --upgrade pip
    
    # for Ubuntu 12.04.*
    sudo pip install setuptools --no-use-wheel --upgrade

    # libpam (necessary for control plane)
    sudo apt-get install -y libpam0g-dev
    
    # serviced needs these for visualization - dirs are in ubuntu 12.04, but not 13.04
    sudo mkdir /sys/fs/cgroup/{blkio,cpuacct,memory}/lxc

    # tmux will make your life better
    sudo apt-get install -y tmux

7. At this point, you need to `set up GitHub for SSH access
   <https://help.github.com/articles/generating-ssh-keys>`_. Also, make sure
   you've been added to the appropriate Zenoss teams.

8. Now it's time to install zendev:

.. code-block:: bash

    # Path to wherever you keep your source. I like ~/src.
    SRCDIR=~/src

    # Switch to your source directory
    cd ${SRCDIR}

    # Clone zendev
    git clone git@github.com:zenoss/zendev

    # Enter the zendev directory
    cd ${SRCDIR}/zendev

    # Generate egg_info as current user to prevent permission problems 
    # down the road
    python ${SRCDIR}/zendev/setup.py egg_info

    # Install zendev in place. This means that changes to zendev source will
    # take effect without reinstalling the package.
    sudo pip install -e ${SRCDIR}/zendev

    # Bootstrap zendev so it can modify the shell environment (i.e., change
    # directories, set environment variables)
    echo 'source $(zendev bootstrap)' >> ~/.bashrc

    # Source it in the current shell
    source $(zendev bootstrap)

9. Create your Europa zendev environment:

.. code-block:: bash

    # Get back to source directory
    cd ${SRCDIR}

    # Create the environment
    zendev init europa

    # Start using the environment
    zendev use europa

10. Add some repositories to the ``europa`` environment:

.. code-block:: bash

    # Add core and serviced repositories from manifests used by the build,
    # which have conveniently been checked out into
    # ~/src/europa/build/manifests
    zendev add $(zendev root)/build/manifests/{core,libs,serviced,zenpacks.core}.json

    # Clone everything
    zendev sync

11. You can now use zendev to edit source, build Zenoss RPMs, build serviced,
    and (if you install Vagrant_ and VirtualBox_) create Vagrant boxes to run
    serviced or Resource Manager. As an example, here's how you build serviced
    and run it:

.. code-block:: bash

    # Ensure you're in the europa environment (you can also use "zendev ls" 
    # to check)
    zendev use europa

    # Go to the serviced source root. cdz is an alias for "zendev cd",
    # automatically set up by the boostrap you sourced in ~/.bashrc.
    cdz serviced

    # Build serviced (may take a while if it's the first time)
    make install

    # Build the Zenoss Docker repo image (also may take a while)
    zendev build devimg

    # Download pre-built opentsdb image from quay.io
    docker login -u zenossinc+alphaeval -e "alpha2@zenoss.com" \
        -p WP0FHD2M9VIKIX6NUXKTUQO23ZEWNSJLGDBA3SGEK4BLAI66HN5EU0BOKN4FVMFF \
        https://quay.io/v1/
    docker pull quay.io/zenossinc/opentsdb:latest

    # Run a totally clean instance of serviced, automatically adding localhost
    # as a host, adding the Zenoss template, and deploying an instance of
    # Zenoss (warning: blows away state!) 
    zendev serviced --reset --deploy

OS X
----
OS X doesn't support Docker natively (although Docker 0.8 ostensibly `adds OS
X support, via boot2docker <http://docs.docker.io/en/latest/installation/mac/>`_). Even if it did, the default case-insensitive filesystem presents a problem if you're doing core Zenoss development (this isn't a problem with serviced). You'll be running things in an Ubuntu Vagrant box in either case.

That said, zendev can still manage your source locally, which will, for
example, allow you to use an IDE in OS X. zendev mounts the environment's
source tree into the Vagrant boxes it creates, so you can modify code directly.
If you don't care about this, you should probably just use the `Vagrant
box`_ to save yourself some effort. Otherwise:

1. Fire up Disk Utility. Create a partition (mine's 50G) formatted with
   a case-sensitive filesystem. Name it, e.g., "Source".
2. Perform steps 6-10, above, with ``/Volumes/Source`` (if you named your
   partition "Source") as the value of ``SRCDIR``.
3. Create an Ubuntu development box and go to town:

.. code-block:: bash

    zendev box create --type ubuntu europa


Windows
-------
Forget it, man. This will only end in tears. Use the `Vagrant box`_.


.. _Vagrant box:
Self-managed Vagrant box
------------------------
Essentially, this is a Vagrant box that has already had steps 1-6 applied.
zendev has the capability to create and manage instances of this box within an
environment, but it's also perfectly good just to start up a VM for
development. 

1. Install Vagrant_ and VirtualBox_ (don't use old versions, please).
2. Make a directory, somewhere, anywhere. ``cd`` into it.
3. Create the box:

.. code-block:: bash

    vagrant init ubuntu-13.04-docker-v1

As the pretty words will tell you, a Vagrantfile will have been created in that
directory. Edit it, uncomment the line specifying the box URL, and set it to
the one we have hosted:

.. code-block:: ruby

    config.vm.box_url = "http://vagrant.zendev.org/boxes/ubuntu-13.04-docker-v1.box"

You should also probably uncomment either the private or public networking line
so you can actually interact with the things running thereon:

.. code-block:: ruby

    config.vm.network :public_network

4. Start the box:

.. code-block:: bash

    vagrant up

5. SSH in and execute steps 6-10, above:

.. code-block:: bash

    vagrant ssh
    # etc.

Update zendev
-------------
Zendev should always be installed from a source checkout, in place. If you want
to update it, you can run:

.. code-block:: bash

    zendev selfupdate


.. _Docker: http://docker.io/
.. _Go: http://golang.org/
.. _Vagrant: http://www.vagrantup.com/downloads.html
.. _VirtualBox: https://www.virtualbox.org/wiki/Downloads
