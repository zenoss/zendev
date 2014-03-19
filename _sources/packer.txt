=================================
Building the Development Base Box
=================================
If you don't have access to, don't want to download, or want to build a custom
version of the Ubuntu development box, you can do so locally using Packer_. The
template is stored in the ``boxes`` directory of your zendev source.

1. `Download Packer <http://www.packer.io/downloads.html>`_. It's a zip file
   containing a bunch of binaries. Unzip it somewhere in your ``PATH``, like
   ``/usr/local/bin``.

2. Install VirtualBox_ if you haven't already.

3. Build the box:

.. code-block:: bash

    # Switch to your zendev checkout (may not be under ~/src)
    cd ~/src/zendev/boxes/ubuntu-13.04-docker

    # Build the box
    packer build ubuntu-13.04-docker.json

4. Now add the box to Vagrant.

.. code-block:: bash

    # First, remove the existing box. If you don't want to remove the existing
    # box, don't do this. Either way, any existing instances will be
    # unaffected.
    vagrant box remove ubuntu-13.04-docker-v1

    # Now add the box you just generated as the new ubuntu-13.04-docker base
    # box. If you didn't remove the one above, pick a new name. You can
    # generate Vagrant boxes using "vagrant init BOXNAME".
    vagrant box add ubuntu-13.04-docker-v1 \
        ~/src/zendev/boxes/ubuntu-13.04-docker*.box

5. Use zendev to create a new instance and see how it turned out:

.. code-block:: bash
    
    zendev box create --type ubuntu mynewbox


.. _Packer: http://www.packer.io/
.. _VirtualBox: https://www.virtualbox.org/wiki/Downloads
