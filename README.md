#zendev

##Description
zendev takes care of setting up and managing the disparate components of a standard Zenoss development environment, 
with or without Control Center. It's primary usecase is to checkout all github repositories needed for 
development and to build a developer focused docker image to run Zenoss in Control-Center. It can also:

* Quickly view branches across some or all repositories
* Automatically set up ``GOPATH``, ``PATH`` and ``ZENHOME`` to point to your zendev environment
* Set up and switch between multiple zendev environments on the same box
* Installs `gvm` for go version management. See https://github.com/moovweb/gvm
* Installs `hub` to extend git functionality. See https://github.com/github/hub

Please feel free to fork and submit pull requests for this project.


##Installation

These instructions are known to work with ubuntu 16.0.4 xenial. Specifially the `newdev-installer` script is known not 
 to work with ubuntu 14.0.4. 

###Host Preparation

For a new developer machine the `newdev-installer` script will prepare machine by installing docker etc. and creating a 
thin pool with an existing device.  

###Without an existing thin pool
Start by identifying an unused device on your system. You can use `lsblk` to seek the devices on your system. 
If unsure of which device to choose, please ask for help.

Once a device has been identified run the following script as your user as long as the user has sudo privileges. 
Replace `/dev/xvdb` with an unused device to create the docker thin pool.

`curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/newdev-installer | bash -s /dev/xvdb`

Alternatively you can run as root but must set the USER environment variable for the script using your desired development user. e.g.

`USER=leeroy_jenkins bash -c "curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/newdev-installer | bash -s /dev/xvdb"`

###With an existing thin pool or use loopback
You can run the newdev-installer if you already have an existing thin pool or just want to run docker with a loopback 
device, not recommended, by passing in `CONF_THINPOOL=false` to the script.  This will install all the tools needed for
 a developer as well as docker but it will not configure docker to use a thinpool. 

`CONF_THINPOOL=false bash -c "curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/newdev-installer | bash"`

Note: Docker may not startup properly if you had it configured for an existing thinpool and use this option. You will 
have to modify the docker config if you want your thinpool to be used.

##GitHub Setup

A GitHub account is needed for the next part. Please make sure you have a GitHub account and that your local git 
installation is setup to use SSH keys. Instructions to setup github to use SSH keys can be found at:  

https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/


##Install zendev

Run the following as your user:

`curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/zendev-installer.sh | bash`

To use zendev immediately without logging in again:
*   `source ~/.bashrc`

##Initialize a zendev environment

1. Go to a directory for checkout.
    * `cd ~/src`
1. Initialiaze an environment, the metis name is arbitrary. This may take some time.
    * `zendev init metis`  
1. Use the previously created environment.
    * `zendev use metis`
1. Build a develepment based zenoss dockerimage. 
    * `zendev devimg`
1. Run zenoss in Control-Center. 
    * `zendev serviced -dxa`  
