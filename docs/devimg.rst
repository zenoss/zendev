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
First step is to create the image, ``zendev/devimg``. You may choose to build
an image that includes any ZenPacks available in your source tree; there is a
shortcut option to build a straight Resource Manager image.

.. code-block:: bash

    # Make sure you have necessary repos (first time only)
    zendev restore develop

    # Build Core image
    zendev build devimg

    # Build Core image + a couple zenpacks
    zendev build devimg -p EnterpriseCollector -p DistributedCollector

    # Build Resource Manager image
    zendev build devimg --resmgr

The image this creates has:
 * Your zendev source root mounted at ``/mnt/src``
 * Your zendev zenhome mounted at ``/opt/zenoss``
 * A full Zenoss source build run
 * ZenPacks installed (ZenJMX and PythonCollector + whatever you specified)
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

    usage: zendev serviced [-h] [-r] [-d] [-a] [-x] [--template TEMPLATE] 
                           [--no-auto-assign-ips] [-u UIPORT] [-- ARG [ARG...]]

    optional arguments:
      -h, --help            show this help message and exit
      -r, --root            Run serviced as root (DEPRECATED. Currently ignored;
                            see --no-root)
      -d, --deploy          Add Zenoss service definitions and deploy an instance
      -a, --startall        Start all services once deployed

      -x, --reset           Clean service state and kill running containers first
      --template            {Zenoss.core,Zenoss.core.full,Zenoss.resmgr.lite,Zenoss.resmgr}
                            Zenoss service template directory to compile and add
      --no-root             Don't run serviced as root
      --no-auto-assign-ips  Do NOT auto-assign IP addresses to services requiring
                            an IP address
      -u UIPORT, --uiport UIPORT
                            UI port (default 443)


Any arguments beyond the standard ``--`` will not be parsed by zendev, and will
instead be passed directly to serviced.

Note: if you use ``--template`` to deploy a Zenoss.resmgr template, you must
previously have built the devimg with the necessary ZenPacks installed.

Now you can make any changes you want to the source on your host, then bounce
the service in the control plane UI or CLI to have your changes take effect.

Attaching to Running Containers: ``zendev attach``
==================================================
There's a simple wrapper for ``nsinit`` called ``zendev attach`` which uses
serviced attach.  For example, to drop into bash on the container running Zope, run:

.. code-block:: bash

    zendev attach zopectl

