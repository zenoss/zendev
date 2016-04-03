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
.. important:: Ubuntu 14.04 or higher is required.
.. no less important:: Ubuntu 14.04 is suggested on AWS.

1. Make sure the universe and multiverse repos are enabled and updated:

    .. code-block:: bash

        # Add the repository
        sudo add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) main universe restricted multiverse"

        # Update the repos
        sudo apt-get update -y

#. Install Docker_:

    .. code-block:: bash

        # Install dependencies
        sudo apt-get install -y curl nfs-kernel-server nfs-common net-tools

        # ------------------------------------------------------------------
        # Install Docker for all other cases, including current Europa work
        # (Uses the latest version of Docker)
        # ------------------------------------------------------------------
        sudo apt-get install apt-transport-https
        sudo apt-key adv --keyserver hkp://pgp.mit.edu:80 \
            --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
        sudo sh -c "echo deb https://apt.dockerproject.org/repo ubuntu-$(lsb_release -sc) main \
            > /etc/apt/sources.list.d/docker.list"
        sudo apt-get update
        sudo apt-get purge lxc-docker*
        sudo apt-get install docker-engine=1.9.1-0~$(lsb_release -sc)

        # Lock the version of Docker so updates won't bump it to a newer version
        sudo apt-mark hold docker-engine


#. Create and configure devicemapper storage for Docker:

    .. code-block:: bash

        # Install lvm tools
        sudo apt-get install lvm2 thin-provisioning-tools

    Add /usr/sbin and /sbin to your path 

    The development machine you were provided should have a second hard drive
    installed for extra storage.  Use that for an LVM thin pool.

    .. code-block:: bash

        # Identify the partition you need to mount
        sudo lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT,UUID

    You'll be looking for an ext4 partition that hasn't been mounted.  Take note of the device name (e.g., /dev/sda1)

    Example output:

    .. code-block:: bash
       :emphasize-lines: 3

        NAME                     FSTYPE        SIZE MOUNTPOINT      UUID
        sda                                  931.5G                 
        └─sda1                   ext4        931.5G                 84ae6065-25fd-4f0a-9fba-40da962ada20
        sdb                                  238.5G                 
        ├─sdb1                   ext2          243M /boot           5a2e2cd4-9a5a-4874-90ba-4195d9400a37
        ├─sdb2                                   1K                 
        └─sdb5                   LVM2_member 238.2G                 yiLydV-Bh6u-X6vH-sLgS-Gjc0-94th-vv76KJ
          ├─it--vg-root (dm-0)   ext4        110.3G /               fcb63cf5-ce47-4cf3-a207-2caa2fad7f4f
          └─it--vg-swap_1 (dm-1) swap        127.9G [SWAP]          b30cf82e-46b4-461f-9f76-d475a8bf3859
        sr0                                   1024M                 


    Set up the LVM thin pool

    .. code-block:: bash

	# Set up parameters for following commands
	# DEV_NAME is the name of the device on your system (e.g., /dev/sda1)
	# VOLUME_GROUP and THIN_POOL can be whatever you want, but these 
	# are reasonable values.
	DEV_NAME=/dev/whatever
	VOLUME_GROUP=docker
	THIN_POOL=pool

	# Create an LVM physical volume and volume group
	sudo vgcreate $VOLUME_GROUP $DEV_NAME

	# Create an LVM thin pool logical volume
	sudo lvcreate -l98%FREE -T $VOLUME_GROUP/$THIN_POOL

	# Note the devicemapper path for the thin pool.  This will be 
	# referenced in the docker configuration.  It should be something 
	# like /dev/mapper/docker-pool
	LV_DMPATH=$(sudo lvs -S lv_attr=~t.\* -o lv_dmpath --noheadings $VOLUME_GROUP | tr -d \ )

        # Depending on the version of lvm, the preceding command may fail.  If
        # it does, you will have to determine the devicemapper path manually.
        # Run the following command, and set LV_DMPATH to the filename appended
        # to /dev/mapper.  It should look like this /dev/mapper/docker-pool-tpool
        sudo dmsetup ls --target=thin-pool
        LV_DMPATH=/dev/mapper/docker-pool-tpool

    Configure docker to use the thin pool

    .. code-block:: bash

	# Populate a docker environment file with devicemapper storage options and the 
	# addresses of the zenoss DNS servers
	sudo sh -c "cat >/etc/default/docker << EOL
	DOCKER_OPTS=\"--storage-driver=devicemapper --storage-opt dm.thinpooldev=$LV_DMPATH --dns 10.87.113.13 --dns 10.88.102.13\"
	EOL"

	# Add the environment file to the docker service
	sudo sed -i 's~\[Service\]~&\nEnvironmentFile=/etc/default/docker~' /lib/systemd/system/docker.service 

	# Add DOCKER_OPTS to the docker startup command
	sudo sed -i 's~ExecStart.*$~& $DOCKER_OPTS~' /lib/systemd/system/docker.service 

	# Stop docker
	sudo systemctl stop docker

	# Clean up existing docker storage
	sudo rm -rf /var/lib/docker

	# Reload docker.service
	sudo systemctl daemon-reload

	# Restart docker
	sudo systemctl start docker

    Reboot your machine to make sure your docker comes up after rebooting!

#. Time for Docker-related configuration.

    Create zenoss user, add it to groups:

    .. code-block:: bash

        # Add the zenoss group/user
        sudo addgroup --gid=1206 zenoss
        sudo adduser --uid=1337 --gid=1206 zenoss
        sudo usermod -a -G docker zenoss
        sudo usermod -a -G sudo zenoss    # if ubuntu
        sudo usermod -a -G awsadmins zenoss    # if ubuntu
        sudo usermod -a -G wheel zenoss   # if RHEL/Centos

        # Login again to get docker group (requires password reentry)
        exec su -l ${USER}

        # Restart Docker
        sudo systemctl restart docker

    Test that you can communicate with the docker daemon:

    .. code-block:: bash

        docker ps

    If you see an empty list of containers (i.e., a row of column names), you're good. 

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

#. Install Go_:

    .. code-block:: bash
    
        # Install "go get" dependencies
        sudo apt-get install -y mercurial bzr git git-flow ngrep telnet vim
    
        # Install the Go version we are using
        sudo apt-get install -y wget curl
        curl -s https://storage.googleapis.com/golang/go1.5.3.linux-amd64.tar.gz | sudo tar -xzC /usr/local
    
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
    
        go get -v github.com/rogpeppe/godef
        go install -v github.com/rogpeppe/godef
        sudo ln -s ${GOPATH}/bin/godef /usr/local/bin/godef
    
        go get -u github.com/nsf/gocode
        sudo ln -s ${GOPATH}/bin/gocode /usr/local/bin/gocode
    
        go get golang.org/x/tools/cmd/goimports
        sudo ln -s ${GOPATH}/bin/goimports /usr/local/bin/goimports

#. Install other dependencies:

    .. code-block:: bash
    
        # Python, pip
        sudo apt-get install -y python-dev python-pip
        sudo pip install --upgrade pip
        
        # Python setup tools (package is named 'python-setuptools' in 'dpkg' output)
        # (We are running Python version 2.7.6)
        sudo pip install setuptools --no-use-wheel --upgrade
    
        # libpam (necessary for control plane)
        sudo apt-get install -y libpam0g-dev
        
        # serviced needs these for visualization - dirs are in ubuntu 12.04, but not 13.04
        sudo mkdir /sys/fs/cgroup/{blkio,cpuacct,memory}/lxc
    
        # tmux or screen will make your life better
        sudo apt-get install -y tmux screen

        # Additional packages needed to build
        sudo apt-get install -y xfsprogs xfsdump libdevmapper-dev
    
        # Need Java to run some of the services (and the build tests)
        sudo apt-get install -y default-jdk

#. At this point, you need to `set up GitHub for SSH access
   <https://help.github.com/articles/generating-ssh-keys>`_. 
   
   When you set up your ssh access, **do not use a key with a passphrase.**

   Also, **make sure you've been added to the appropriate Zenoss teams**.

#. Now it's time to install zendev:
    
    .. code-block:: bash
    
        # Path to wherever you keep your source. I like ~/src.
        SRCDIR=~/src
    
        # If SRCDIR does not exist, create it
        mkdir -p ${SRCDIR}
    
        # Switch to your source directory
        cd ${SRCDIR}
    
        # Clone zendev
        git clone git@github.com:zenoss/zendev
    
        # If you get an access denied error cloning the repository, you haven't
        # been added to the appropriate Zenoss teams (see the previous step).
    
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

#. Create your zendev environment for europa:

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

#. Create your zendev environment for NFVi:

    .. code-block:: bash
    
        # Get back to source directory
        cd ${SRCDIR}
    
        # Create the environment for building core devimg
        zendev init nfvi --tag support/5.1.x-nfvi
    
        # Start using the environment
        zendev use nfvi
    
        # This may be needed if the above zendev init failed to clone some repos
        zendev sync
    
        # Go to the serviced source root. cdz is an alias for "zendev cd",
        # automatically set up by the boostrap you sourced in ~/.bashrc.
        cdz serviced
    
        # Build serviced (may take a while if it's the first time)
        # The following will build and copy serviced to $GOPATH/bin which
        # is already in your search path established by zendev.
        make
    
        # Build the Zenoss Docker repo image (also may take a while)
        zendev build --nfvi devimg    # to build nfvi-resmgr
    
        # Run a totally clean instance of serviced, automatically adding localhost
        # as a host, adding the Zenoss template, and deploying an instance of
        # Zenoss (warning: blows away state!) 
        zendev serviced --reset --deploy --template nfvi  # to deploy nfvi


#. You can now use zendev to edit source, build Zenoss RPMs, build serviced,

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

    If you encounter an error related to permissions while building serviced, you can
    resolve the issue by changing the owner of the directory.

    .. code-block:: bash
    
        sudo chown ${USER} /usr/local/go/pkg/tool/linux_amd64/vet
    
    Proceed after seeing the Zenoss template in 'Deployed templates'.

    Example output:

    .. code-block:: bash

        Deployed templates:
        TemplateID                            Name             Description
        639b8be8e7abf1fdce1260d2521f5fd0      Zenoss.core      Zenoss Core


    When you see this, you should be able to launch Control Center from https://localhost/

#. Setting up hosts entries

    Log in to Control Center and click on Zenoss.core under the applications list.

    You'll have multiple Virtual Host Names listed.

    Sample output:

    .. code-block:: bash

        Virtual Host Name   Service         Endpoint                URL
        hbase               HMaster         hbase-masterinfo-1      https://hbase.zenoss-1273 	
        opentsdb            opentsdb        opentsdb-reader         https://opentsdb.zenoss-1273 	
        rabbitmq            RabbitMQ        rabbitmq_admin          https://rabbitmq.zenoss-1273 	
        zenoss5             Zenoss.core     zproxy                  https://zenoss5.zenoss-1273 	

    For each of the URLs listed, you'll need to add host entries into the /etc/hosts file.
    **sudo** edit the file with your choice of editors, and append the host names to the
    localhost entry.

    Find the public IP of your dev box and replace **<public ip>** below, adding the hosts in
    the URL list from CC.

    Sample of the first two lines in the /etc/hosts file:

    .. code-block:: bash
       :emphasize-lines: 2

        127.0.0.1       localhost
        <public ip>     zenoss-1273 zenoss5.zenoss-1273 hbase.zenoss-1273 opentsdb.zenoss-1273 rabbitmq.zenoss-1273

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
