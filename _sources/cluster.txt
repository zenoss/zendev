=================
Vagrant Clusters
=================
The zendev cluster command allows you to provision clusters of Vagrant boxes
with your source tree mounted, zendev installed, and the zendev environment set
up on each of them.  The cluster is configured to make multihost serviced
development easy.

Creating a Vagrant Cluster
--------------------------
``zendev cluster create`` will create a Vagrant cluster on a private network for
multi-host testing.  The nodes will be set up to run as agents, with the master running
on the host development machine.

The cluster must be given a name that will be used to manage the whole cluster.
The individual box names are derived from the cluster name by appending a two
digit number to the cluster name. The number of boxes
in a cluster is specified by the ``count`` option. The amount of memory allocated
to each box is specified by the ``memory`` option.  The number of cpus allocated to
each box is specified by the ``cpus`` option.

Acceptable box types are: ``ubuntu``, ``fedora``, ``controlplane``, and ``sourcebuild``.
The default is ``ubuntu``.

It is also possible to create one or more btrfs volumes on each vm.  The number of
btrfs volumes is specified with the by the ``btrfs`` option.  The size of the btrfs
volumes is controlled by the ``fssize`` option.  The first two volumes are mounted
at /var/lib/docker and /opt/serviced/var respectively.

.. code-block:: bash

    # Create a new cluster named demo containing 5 ubuntu boxes
    zendev cluster create --type ubuntu --count 5 demo

    # Create a new cluster of 3 ubuntu boxes named 4p with 2MB of RAM each
    zendev cluster create --type ubuntu --count 3 --memory 2048 4p


Listing Clusters
----------------
``zendev cluster ls`` displays a list of available clusters.

.. code-block:: bash

    # List all the clusters
    zendev cluster ls
    
To list the boxes within a cluster, specify the cluster name: ``zendev cluster ls CLUSTER``

.. code-block:: bash

    # List boxes in the cluster named CLUSTER
    zendev cluster ls CLUSTER

Start a cluster
--------------------
``zendev cluster up`` will start all the boxes in a given cluster.

.. code-block:: bash

    # Start all the boxes in the cluster named CLUSTER
    zendev cluster up CLUSTER

``zendev cluster up`` can be used to start a single box in a given cluster.

.. code-block:: bash

    # Start the box named BOX in the cluster CLUSTER
    zendev cluster up CLUSTER BOX

Halt a cluster
----------------------------------------
``zendev cluster halt`` will stop all the boxes in a given cluster.

.. code-block:: bash

    # Stop all the boxes in the cluster named CLUSTER
    zendev cluster halt CLUSTER

``zendev cluster halt`` can also be used to halt a specified box in a given cluster.

.. code-block:: bash

    # Stop the box named BOX in cluster CLUSTER
    zendev cluster halt CLUSTER BOX

Login to a box in a cluster
---------------------------
``zendev cluster ssh`` allows you to login to a specific box in a given cluster.

.. code-block:: bash

    # Login to the box named BOX in cluster CLUSTER
    zendev cluster ssh CLUSTER BOX

Destroy a cluster
-----------------
``zendev cluster destroy`` rids the world of the specified cluster

.. code-block:: bash

    # Destroy the cluster named CLUSTER
    zendev cluster destroy CLUSTER


Example: Creating and running a multi-host network
-----------------------------------------
All nodes in the network are set up to run as agents of a master running on the host.
All nodes share the ``devimg`` mounts, so that they all run the same code.

.. code-block:: bash

    # Create a cluster with one node
    zendev cluster create foo

    # Start CC master on the host
    # "--cluster-master" instructs zendev to run with SERVICED_REGISTRY and
    #   SERVICED_OUTBOUND_IP set appropriately
    zendev serviced -dx --cluster-master

    # Start CC agent on the VM
    # '--skip-ready-wait' tells zendev not to poll CC for ready status
    zendev cluster ssh foo
    zendev serviced --skip-ready-wait

*Note*:
Currently serviced does not allow non-serviced controlled nfs exports.  Unfortunately,
zendev needs to nfs mount the zenhome directory into the VM (vboxsf mounts do not work
as they do not support chown.)  serviced overwrites the /etc/hosts.allow file when it
starts up; virtualbox amends that file when it boots the VM.  Therefore, it is necessary
to reboot the VMs each time serviced on the host is restarted.