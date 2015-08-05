============
Installation
============

Other things being equal, Zenoss development as a whole is easiest on Ubuntu.
That said, zendev can work on any platform that isn't Windows, and includes an
Ubuntu Vagrant box already set up with the proper dependencies.

Here's how to set up a full Zenoss development environment on Ubuntu (in case
you were wondering, these instructions go far beyond the requirements for
zendev itself, which are basically git and Python).

**Note**: In the rare case that you are installing on a box that previously had 
a non-zendev instance of Resource Manager, reinstall docker.
Specifically, you need to delete /etc/default/docker or revert the DOCKER_OPTS
setting to the initial --dns option. Just apt-get remove lxc-docker-1.5.0 and
reinstall it.

Ubuntu
------
.. important:: Ubuntu 14.04 or higher is required.  Make sure you know the release name
	       for your version of Ubuntu (the Adjective from `this table
	       <https://wiki.ubuntu.com/DevelopmentCodeNames#Release_Naming_Scheme>`_).
	       Use it (with all small letters) in place of URELEASE in the instructions below.

1. Make sure the universe and multiverse repos are enabled and updated:

.. code-block:: bash

    # Add the repository
    sudo add-apt-repository "deb http://archive.ubuntu.com/ubuntu URELEASE main universe restricted multiverse"

    # Update the repos
    sudo apt-get update

2. Install Docker_:

.. code-block:: bash

    # Install dependencies
    sudo apt-get install -y curl nfs-kernel-server nfs-common net-tools

    # ------------------------------------------------------------------
    # Install Docker for old Europa (version 1.0.x)
    # ------------------------------------------------------------------
    sudo apt-get install apt-transport-https
    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 \
         --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
    sudo sh -c "echo deb https://get.docker.com/ubuntu docker main \
         > /etc/apt/sources.list.d/docker.list"
    sudo apt-get update
    sudo apt-get install lxc-docker-1.5.0

    # ------------------------------------------------------------------
    # -OR-
    # Install Docker for current Europa work (version 1.1 or later)
    # ------------------------------------------------------------------
    sudo apt-get install apt-transport-https
    sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 \
	 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    sudo vim /etc/apt/sources.list.d/docker.list
        # remove the contents and replace with the following:
        deb https://apt.dockerproject.org/repo ubuntu-URELEASE main
    apt-get update
    apt-get purge lxc-docker*
    apt-get install docker-engine

    # ------------------------------------------------------------------
    # -OR-
    # Install Docker for all other cases
    # ------------------------------------------------------------------
    curl -sSL https://get.docker.io/ubuntu/ | sudo sh


If you are operating under AWS, check if docker is using the devicemapper driver.
    Run the "sudo docker info" command and look at the storage driver section. If it
    says "devicemapper", stop docker, install linux-image-extra, and reinstall
    docker to use AUFS as a storage driver.

.. code-block:: bash

    sudo stop docker
    sudo apt-get remove lxc-docker
    sudo apt-get autoremove
    sudo rm -rf /var/lib/docker
    sudo apt-get update
    sudo apt-get install linux-image-extra-`uname -r`
    sudo apt-get install lxc-docker-1.5.0

3. Time for Docker-related configuration.

Add your user to the ``docker`` group:

.. code-block:: bash

    # Add the current user to the docker group
    sudo usermod -a -G docker ${USER}
    sudo usermod -a -G sudo ${USER}    # if ubuntu
    sudo usermod -a -G wheel ${USER}   # if RHEL/Centos

    # Login again to get docker group (requires password reentry)
    exec su -l ${USER}

    # Restart Docker
    sudo service docker restart

Test that you can communicate with the docker daemon:

.. code-block:: bash

    docker ps

If you see an empty list of containers (i.e., a row of column names), you're
good. 

Next, modify ``/etc/security/limits.conf`` to up the file limits:

.. code-block:: bash

    cat <<\EOF | sudo /bin/bash -c "cat >> /etc/security/limits.conf"
    *      hard   nofile   1048576
    *      soft   nofile   1048576
    root   hard   nofile   1048576
    root   soft   nofile   1048576
    EOF

Then reboot, to make sure the new limits take effect.

Set up your hub.docker.com credentials.  Go to here: https://hub.docker.com/account/signup/.  Send Ian an email with your Docker Hub username and real name.  Your credentials will be added to groups so you get access to our private repositories (Resource Manager, Impact, etc.).

When your box comes back up, authenticate to hub.docker.com:

.. code-block:: bash

    docker login -u YOUR_DOCKERHUB_USERNAME -e "you@zenoss.com"

4. Install Go_:

.. code-block:: bash

    # Install "go get" dependencies.
    sudo apt-get install -y mercurial bzr git

    # ------------------------------------------------------------------
    # Install Go for old Europa (version 1.0.x)
    # ------------------------------------------------------------------
    sudo apt-get install -y wget curl
    curl -s https://storage.googleapis.com/golang/go1.3.3.linux-amd64.tar.gz | sudo tar -xzC /usr/local

    # ------------------------------------------------------------------
    # -OR-
    # Install Go for all other cases, including current Europa work
    # ------------------------------------------------------------------
    sudo apt-get install -y wget curl
    curl -s https://storage.googleapis.com/golang/go1.4.2.linux-amd64.tar.gz | sudo tar -xzC /usr/local

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

    go get golang.org/x/tools/cmd/goimports
    sudo ln -s ${GOPATH}/bin/goimports /usr/local/bin/goimports

5. Install other dependencies:

.. code-block:: bash

    # Python, pip
    sudo apt-get install -y python-dev python-pip
    sudo pip install --upgrade pip
    
    # Python setup tools (package installed is actually 'python-setuptools')
    # (We are running Python version 2.7.6)
    sudo pip install setuptools --no-use-wheel --upgrade

    # libpam (necessary for control plane)
    sudo apt-get install -y libpam0g-dev
    
    # serviced needs these for visualization - dirs are in ubuntu 12.04, but not 13.04
    sudo mkdir /sys/fs/cgroup/{blkio,cpuacct,memory}/lxc

    # tmux or screen will make your life better
    sudo apt-get install -y tmux screen

And, if you're working on Europa:

.. code-block:: bash
    
    # Additional packages needed to build
    sudo apt-get install -y xfsprogs xfsdump
    sudo apt-get install -y libdevmapper-dev

    # Need Java to run some of the services (and the build tests)
    sudo apt-get install -y default-jdk

6. At this point, you need to `set up GitHub for SSH access
   <https://help.github.com/articles/generating-ssh-keys>`_. 
   
   When you set up your ssh access, **do not use a key with a passphrase.**  Also, 
   make sure you've been added to the appropriate Zenoss teams.

7. Now it's time to install zendev:

.. code-block:: bash

    # Path to wherever you keep your source. I like ~/src.
    SRCDIR=~/src

    # If SRCDIR does not exist, create it
    mkdir -p ${SRCDIR}

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

8. Create your Europa zendev environment:

.. code-block:: bash

    # Get back to source directory
    cd ${SRCDIR}

    # Create the environment for building core devimg
    zendev init europa --tag develop

    # Start using the environment
    zendev use europa

    # This may be needed if the above zendev init failed to clone some repos
    zendev sync

    # Optional: add enterprise zenpacks for building resmgr devimg
    zendev add ~/src/europa/build/manifests/zenpacks.commercial.json

9. You can now use zendev to edit source, build Zenoss RPMs, build serviced,
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
    # The following will build and copy serviced to $GOPATH/bin which
    # is already in your search path established by zendev.
    make

    # Build the Zenoss Docker repo image (also may take a while)
    zendev build devimg             # to build core
    # -OR-
    zendev build --resmgr devimg    # to build resmgr

    # Run a totally clean instance of serviced, automatically adding localhost
    # as a host, adding the Zenoss template, and deploying an instance of
    # Zenoss (warning: blows away state!) 
    zendev serviced --reset --deploy                                # to deploy core
    # -OR-
    zendev serviced --reset --deploy --template Zenoss.resmgr.lite  # to deploy resmgr lite

    # Proceed after seeing the Zenoss template in 'Deployed templates'

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
2. Perform steps 6-9, above, with ``/Volumes/Source`` (if you named your
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
Essentially, this is a Vagrant box that has already had steps 1-4 and part of 5 applied.
zendev has the capability to create and manage instances of this box within an
environment, but it's also perfectly good just to start up a VM for
development.

**Note:** Currently this box has Docker 1.5.0 installed.

1. Install Vagrant_ and VirtualBox_ (don't use old versions, please).
2. Make a directory, somewhere, anywhere. ``cd`` into it.
3. Create the box:

.. code-block:: bash

    vagrant init ubuntu-14.04-CC-1.x

As the pretty words will tell you, a Vagrantfile will have been created in that
directory. Edit it and uncomment or add the following line, setting the URL as shown.

.. code-block:: ruby

    config.vm.box_url = "http://vagrant.zendev.org/boxes/ubuntu-14.04-CC-1.x.box"

You should also probably uncomment either the private or public networking line
so you can actually interact with the things running thereon:

.. code-block:: ruby

    config.vm.network "public_network"

4. Optionally, install any plugins.  For example, the scp plugin, which will
   allow you to copy files to the box:

.. code-block:: bash

   vagrant plugin install vagrant-scp

5. Start the box and log in to it:

.. code-block:: bash

    vagrant up
    vagrant ssh

6. Execute steps 3 and 5-9 from the Ubuntu section above.

   Notice in step 5, some of the software is already installed.  ``dpkg -l`` is your friend here.

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
