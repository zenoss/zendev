=========================
Working With Repositories
=========================

zendev can keep track of all the repositories associated with a project. Groups
of repositories are described by simple JSON manifests that can be added to an
environment. zendev can then help you navigate to repositories on the
filesystem, clone new repos, pull down changes and rebase your feature
branches, push your existing changes, etc.

Manifests
---------
A manifest is a JSON file of this structure:

.. code-block:: json
    
    {
        "repos": {
            "<PATH>": {
              "repo": "<OWNER>/<REPONAME>",
              "ref": "<BRANCH>"
            },
            ...
        }
    }

PATH is the path relative to your environment's source root where the
repository should be cloned. OWNER and REPONAME are the GitHub repository owner
and name, respectively. BRANCH is the branch that should be checked out.

Both the Zenoss build system and zendev use the same manifest structure; it
effectively makes portable the source tree necessary to build or develop
a project.

The manifests representing the Zenoss and Control Plane projects live in the
GitHub repository ``zenoss/platform-build``, `in the manifests directory
<https://github.com/zenoss/platform-build/tree/develop/manifests>`_. This
repository is checked out as a part of every zendev environment, and can be
found in ``$(zendev root)/build``.

Adding Manifests
----------------
You can add a manifest to a zendev environment with the ``add`` command:

.. code-block:: bash

    zendev add /path/to/manifest.json

Navigating Source
-----------------
zendev provides a utility allowing you to ``cd`` directly to any repository
described in the added manifests using regex matching. This is
(appropriately) provided by the ``cd`` command. For example:

.. code-block:: bash

    # cd to $(zendev root)/src/golang/src/github.com/zenoss/serviced
    zendev cd serviced

    # cd to $(zendev root)/src/golang/src/github.com/zenoss/metricshipper
    zendev cd shipper

    # cd to $(zendev root)/src/zenpacks/ZenPacks.zenoss.LDAPMonitor
    zendev cd ldap

``cdz`` is an alias for ``zendev cd`` installed by the zendev bootstrap.

Removing Repositories
---------------------
Repositories can be removed from the environment using the ``rm`` command,
again using regex matching:

.. code-block:: bash

    # Removes, e.g., src/zenpacks/ZenPacks.zenoss.LDAPMonitor
    zendev rm ldap

Generating Manifests
--------------------
Although simple to create by hand, manifests can be generated using the
``freeze`` command, which will output your environment's current repository
state as a manifest, including current branches. Simply issue the command:

.. code-block:: bash

    zendev freeze > mynewmanifest.json

This enables you to describe the branches necessary to, e.g., build
a particular release or feature sandbox that may have changes spanning several
repositories.

Pulling/Pushing Changes
-----------------------
``zendev sync`` will clone any repositories that haven't been cloned yet, and
pull any changes from and push any locally committed changes to GitHub.
Repositories can be specified like most other commands, using string matching.
Default is to sync all repositories.

Status
------
zendev prints a table describing current branch and change status for
specified (or all) repositories as a result of the ``status`` command:

.. code-block:: bash

    # Default: print status for repositories with uncommitted changes
    zendev status

    # Print status for repositories matching one or more strings
    zendev status metric ldap

    # Print status for all repositories
    zendev status -a


