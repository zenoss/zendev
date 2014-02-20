==========================
Working With Vagrant Boxes
==========================
zendev comes with a facility for provisioning Vagrant boxes with your source
tree mounted, zendev installed and the same zendev environment set up. Two
types of Vagrant boxes are built in:
* An Ubuntu 13.04 base box with all dependencies necessary to develop the
  control plane
* A Fedora 19 base box with all dependencies necessary to build Zenoss RM from
  source or install from RPM

Creating a Vagrant Box
----------------------
``zendev box create`` will create a Vagrant box of the type specified, provision it
appropriately, and ssh in. All boxes are created in the same private network;
private IPs are allocated by `a Vagrant plugin
<https://github.com/adrienthebo/vagrant-auto_network>`_ that zendev will
install for you if you don't have it already.

Acceptable types are: ``ubuntu``, ``fedora``, ``controlplane`` (synonym of
``ubuntu``) and ``sourcebuild`` (synonym of ``fedora``). 

Boxes must also be given a name that can be used to manage the box with zendev.

.. code-block:: bash

    # Create a new Ubuntu-based Vagrant box
    zendev box create --type ubuntu cplanedev

    # Create a new Fedora-based Vagrant box
    zendev box create --type fedora rmdev

SSHing to Boxes
---------------
``zendev box ssh BOX`` (aliased to ``zendev ssh`` for convenience) will,
unsurprisingly, start an SSH session on the Vagrant box named.

Listing Boxes
-------------
List all the boxes in your environment with ``box ls``:

.. code-block:: bash

    # List paths to all Vagrant boxes
    zendev box ls

Managing Boxes
--------------
.. code-block:: bash

    # Halt a box named BOX
    zendev box halt BOX

    # Start a box named BOX
    zendev box up BOX

Destroying Boxes
----------------
.. code-block:: bash

    # Destroy box named BOX
    zendev box destroy BOX
