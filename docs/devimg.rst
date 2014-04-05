======================================
Developing Zenoss in the Control Plane
======================================
Since serviced runs Zenoss services from an image, development of Zenoss per se
would typically mean making changes, committing them to an image, then
restarting the services to pick up the new image. zendev simplifies this
process by creating a lightweight image that mounts Zenoss source from your
host filesystem.

Building the Image
==================
First step is to create the image, ``zendev/devimg``. Currently, only Core is
available at this high level, although the underlying steps are there to
support Resource Manager as well. Time permitting! Contributions welcome! Run:

.. code-block:: bash

    # Make sure you have necessary repos (first time only)
    zendev add $(zendev root)/build/manifests/{core,zenpacks.core}.json
    zendev sync

    # Build
    zendev build devimg

The image this creates has:
 * Your zendev source root mounted at ``/mnt/src``
 * Your zendev zenhome mounted at ``/opt/zenoss``
 * A full Zenoss source build run
 * Some ZenPacks installed (currently ZenJMX and PythonCollector, since they
   have service definitions in Zenoss.core)
 * ``$(zendev root)/src/core/Products`` symlinked to ``/opt/zenoss/Products``
 * A `zenoss` user with the same GID/UID as your current user, so you don't
   have permission problems with the mounted source (sudoer, NOPASSWD)

For the most part, since ``ZENHOME``, ``SRCROOT``, ``GOPATH``, etc. are all the
same on the host as in the image, you should be able to run ``make; make
install`` for a component on your host, or edit source in Products directly,
and have it all work out so that the image serviced uses gets those changes
without having to do any image rebuilding.

Running Control Plane
=====================
Once your image exists, you can start the control plane using ``zendev
serviced`` (this replaces ``zendev resetserviced``).

.. code-block:: bash

    usage: zendev serviced [-h] [-r] [-d] [-a] [-x] [-- ARG [ARG...]]

    optional arguments:
      -h, --help      show this help message and exit
      -r, --root      Run serviced as root
      -d, --deploy    Add Zenoss service definitions and deploy an instance
      -a, --startall  Start all services once deployed
      -x, --reset     Clean service state and kill running containers first

Any arguments beyond the standard ``--`` will not be parsed by zendev, and will
isntead be passed directly to serviced.

Now you can make any changes you want to the source on your host, then bounce
the service in the control plane UI or CLI to have your changes take effect.

Attaching to Running Containers: ``zendev attach``
==================================================
There's a simple wrapper for ``nsenter`` called ``zendev attach``. For example,
to drop into bash on the container running Zope, run:

.. code-block:: bash

    zendev attach zopectl

Installing ``nsenter``
----------------------
You'll need util-linux installed for zendev attach to work. Here's how (the
version in the repos is too old):

.. code-block:: bash

    wget -O- https://www.kernel.org/pub/linux/utils/util-linux/v2.24/util-linux-2.24.tar.bz2 | tar -C /tmp -xj
    cd /tmp/util-linux-2.24/
    ./configure --without-ncurses --prefix=/usr/local/util-linux; make; sudo make install
    sudo cp -p /usr/local/util-linux/bin/nsenter /usr/local/bin
