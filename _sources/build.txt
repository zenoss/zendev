===========================
Building Zenoss With zendev
===========================
Every zendev environment has a copy of the `platform-build repository
<http://github.com/zenoss/platform-build>`_ and knows how to build Zenoss using
the environment's source tree. This is, in effect, the new Zenoss build system.

Building from Source
====================
This should (currently) only be attempted on the provided Fedora base box.
Simply issue the command:

.. code-block:: bash

    zendev build srcbuild

Since zendev already set up ``ZENHOME`` to ``$(zendev root)/zenhome``, that's
where it will end up.

Although Zenoss will be built using the environment's source tree, zendev does
NOT currently symlink Products/bin from the source tree into ``$ZENHOME``,
a common development environment practice. Contributions welcome.

Building RPMs
=============
The only requirement to build RPMs is Docker. zendev will create a Docker image
that can build an RPM, mount the appropriate source directories, build the RPM,
and copy it to an output directory mounted from the host.

.. code-block:: bash

    # Build Core
    zendev build core

    # Build RM (Core + ZenPacks). Requires that the *zenpack.json manifests are
    # added to the environment.
    zendev build resmgr

