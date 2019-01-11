#zendev

# Table of Contents
  - [Description](#description)
  - [Installation](#installation)
    - [Host Preparation](#host-preparation)
    - [Without an existing thin pool](#without-an-existing-thin-pool)
    - [With an existing thin pool or use loopback](#with-an-existing-thin-pool-or-use-loopback)
  - [GitHub Setup](#github-setup)
  - [Install zendev](#install-zendev)
  - [Initialize a zendev environment](#initialize-a-zendev-environment)
  - [Building Images](#building-images)
    - [Building Product Images](#building-product-images)
    - [Building Dev Images](#building-dev-images)
  - [Testing With devimg](#testing-with-devimg)
  - [Frequently Asked Questions](#frequently-asked-questions)

## Description

zendev takes care of setting up and managing the disparate components of a standard Zenoss development environment,
with or without Control Center. It's primary usecase is to checkout all github repositories needed for
development and to build a developer focused docker image to run Zenoss in Control-Center. It can also:

* Quickly view branches across some or all repositories
* Automatically set up ``GOPATH``, ``PATH`` and ``ZENHOME`` to point to your zendev environment
* Set up and switch between multiple zendev environments on the same box
* Installs `gvm` for go version management. See https://github.com/moovweb/gvm
* Installs `hub` to extend git functionality. See https://github.com/github/hub

Please feel free to fork and submit pull requests for this project.


## Installation

These instructions are known to work with ubuntu 16.0.4 xenial. Specifically the `newdev-installer` script is known not
 to work with ubuntu 14.0.4.

### Host Preparation

For a new developer machine the `newdev-installer` script will prepare machine by installing docker etc. and creating a
thin pool with an existing device.

### Without an existing thin pool
Start by identifying an unused device on your system. You can use `lsblk` to seek the devices on your system.
If unsure of which device to choose, please ask for help.

Once a device has been identified run the following script as your user as long as the user has sudo privileges.
Replace `/dev/xvdb` with an unused device to create the docker thin pool.

`curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/newdev-installer | bash -s /dev/xvdb`

Alternatively you can run as root but must set the USER environment variable for the script using your desired development user. e.g.

`USER=leeroy_jenkins bash -c "curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/newdev-installer | bash -s /dev/xvdb"`

### With an existing thin pool or use loopback
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


## Install zendev

Run the following as your user (*NOTE: run from a plain shell, i.e. not within a zendev environment*):

`curl -s -S -L https://raw.githubusercontent.com/zenoss/zendev/zendev2/binscripts/zendev-installer.sh | bash`

To use zendev immediately without logging in again:
*   `source ~/.bashrc`

## Initialize a zendev environment
_Note: The new zendev2 environment is not compatible with the older zendev environment.  Thus, you cannot use an existing (old zendev) environment with zendev2.
If you have an existing (old zendev) environment and you wish to continue using the same name with zendev2 you must remove/rename the existing environment's directory._

1. Go to a directory for checkout.
    * `cd ~/src`
1. Initialize an environment, the metis name is arbitrary. This may take some time.
    * `zendev init metis`
1. Use the previously created environment.
    * `zendev use metis`
1. Build a development based zenoss docker image.
    * `zendev devimg`
1. Build Control-Center.
    * `cdz serviced; make clean build`
1. Run zenoss in Control-Center.
    * `zendev serviced -dxa`

## Building Images

### Building Product Images
In this context, "product image" means an image as we deliver it to customers. At the time of this writing,
there are only two such images: core and resmgr.  The product images built by zendev use "DEV" as the both the image 'maturity' label and the build number.  For instance, where as a nightly build might result in an image named something like `zenoss/core_5.2:5.2.0_129_unstable`, an execution of `zendev build` will result in an image named `zenoss/core_5.2:5.2.0_DEV_DEV`.

### Syntax Overview
```
$ zendev build --help
usage: zendev build [-h] [-c] TARGET

positional arguments:
  TARGET       Name of the target product to build; e.g. core, resmgr, etc

optional arguments:
  -h, --help   show this help message and exit
  -c, --clean  Delete any existing images before building
```

### Examples
Build core, removing any previous image
```
$ zendev devimg -c
```

Build CZ
```
$ zendev devimg -c -p cse
```

### Under the hood
Building product images should NOT be an opaque process.  Zendev is not required to build product images.
In fact, the nightly build process does NOT use `zendev build` - `zendev/build` is simply a convenient shortcut.

Two simple make commands in the [zenoss/product-assembly](https://github.com/zenoss/product-assembly) repo
will handle the actual work of building the image.
The first step is to build the `zenoss/product-base` image which is common to all Zenoss products.
The second step is to build the specific product image (e.g. `zenoss/core_5.2`).

Here is the equivalent of `zendev build --clean core`:
```
$ cdz product-assembly
$ cd product-base
$ make clean build
$ cd ../core
$ make clean build
```

### Building Dev Images
`zendev/devimg` is a specialized image for use in testing Zenoss services with `zendev serviced` and `zendev test`.
The main characteristics that set devimg apart from standard product images are:
* devimg contains a variety of developer tools to assist with debugging (e.g Maven and the JDK).
* the uid/gid of the `zenoss` user in the image is remapped to the current developer's uid/gid.
* the developer's `$(ZENDEV_ROOT)/zenhome` directory is initialized with the ZENHOME contents of a standard product image.
* a variety of different softlinks and mount points are created such that when the container is started with proper mounts, all of the developer's source code for Zenoss components and ZenPacks will be mounted into the image.
* all zenpacks are link-installed into the image.
* both `zendev serviced` and `zendev test` understand how to mount the right directories into the `zendev/devimg` container.

By default, `zendev/devimg` has only the PythonCollector ZenPack installed, because that ZenPack is required to start Zenoss.
Different command options allow the developer to control which set of ZenPacks to link-install into the image.

### Syntax Overview
```
$ zendev devimg --help
usage: zendev devimg [-h] [-c] [-p PRODUCT | -f FILE | -z ZENPACKS]

optional arguments:
  -h, --help            show this help message and exit
  -c, --clean           Delete any existing devimg before building a new one
  -p PRODUCT, --product PRODUCT
                        Name of a Zenoss product that defines the set of
                        zenpacks copied into the image; e.g. core, resmgr, etc
  -f FILE, --file FILE  Path to a zenpacks.json file that defines the set of
                        zenpacks copied into the image
  -z ZENPACKS, --zenpacks ZENPACKS
                        Comma-separated list of ZenPack names to copy into the
                        image
```
### Examples
Build devimg with no zenpacks
```
$ zendev devimg
```

Build devimg with the same set of zenpacks used in RM
```
$ zendev devimg -p resmgr
```

## Testing With devimg
`zendev test` is used for running platform and/or ZenPack unit-tests using the `zendev/devimg` image.
If you want to selective run certain tests, it helps to understand a little bit of how the tests are run.
After `zendev/devimg` is started, and the default test execution occurs in two phases:
* the Zenoss product runtime is started by running the command `${ZENHOME}/install_scripts/startZenossForTests.sh`
* the Zenoss test runner is launched by running the command `su - zenoss  -c "${ZENHOME}/bin/runtests $*"`

Notice the last argument of the last command, `$*` - to pass in arguments to the Zenoss test runner, `runtests`, you must preceed the argument with `--`, something like `zendev test -- --no-zenpacks`. To see all of the options for `runtests`, use `zendev test -- --help`

### Syntax Overview
```
$ zendev test --help
usage: zendev test [-h] [-i] [-n] ...

positional arguments:
  arguments

optional arguments:
  -h, --help         show this help message and exit
  -i, --interactive  Start an interactive shell instead of running the test
  -n, --no-tty       Do not allocate a TTY
```

### Examples
Run all tests against the current devimg; i.e. prodbin tests + tests for all installed zenpacks (if any)
```
$ zendev test
```

Run just the tests for prodbin (no zenpacks)
```
$ zendev devimg --clean
$ zendev test -- --no-zenpacks
```

Run the tests for a single ZenPack (in this case, a ZenPack defined in the core image)
```
$ zendev devimg --clean -p core
$ zendev test -- --type=unit --name ZenPacks.zenoss.LinuxMonitor
```

Run the tests interactively. Note that you must first start the Zenoss runtime. Once the Zenoss has started, you can run whatever test(s) you want using the `runtests` script.
```
$ zendev test -i
[root@0f7b409c35ae /]# /opt/zenoss/install_scripts/startZenossForTests.sh
[root@0f7b409c35ae /]# su - zenoss
(zenoss) [zenoss@0f7b409c35ae ~]$ runtests --help
```

## Frequently Asked Questions

**Why doesn't `cdz` work?**
If you experience problems running cdz edit your `~/.bashrc` file and ensure that the line `source $(zendev bootstrap)` occurs _after_ the addition
of the directory `${HOME}/.local/bin` to your PATH.  If you make changes to your `.bashrc` file be sure to either close and reopen your shell or
run `source ~/.bashrc`.

**Why wont the docker-registry service start?**
If `zendev serviced` doesn't successfully come up and you see a message like:
```
ERRO[0133] Unable to start internal service              error=healthcheck timed out isvc=docker-registry location=manager.go:379 logger=isvcs
```
The problem can be that the docker-registry healthcheck is trying to connect to the local ip6 address and not the ip4 address. Look in /etc/hosts and make sure the ip6 entries are not mapping `localhost`. If they are, change it to something like `ip6-localhost`. 
