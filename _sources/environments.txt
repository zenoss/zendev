=========================
Working With Environments
=========================
The base zendev entity is the *environment*. An environment represents:

* A source tree
* A set of Vagrant boxes
* A particular ``GOPATH`` and ``ZENHOME``

The path to the current environment is always readily accessible:

.. code-block:: bash

    # Prints path to the root of the environment
    zendev root

Creating an Environment
-----------------------
.. code-block:: bash

    # Create a new zendev environment at $PWD/ENVIRONMENT
    zendev init ENVIRONMENT

Listing Environments
--------------------
.. code-block:: bash

    # List all environments. The current one will be indicated with an
    # asterisk.
    zendev ls

Using an Environment
--------------------
.. code-block:: bash

    # Switch to the environment named ENVIRONMENT
    zendev use ENVIRONMENT

Using an environment will:

* Set ``GOPATH`` to ``$(zendev root)/src/golang``
* Set ``PATH`` to ``$(zendev root)/src/golang/bin:${PATH}``
* Set ``ZENHOME`` to ``$(zendev root)/zenhome``

Deleting an Environment
-----------------------
.. code-block:: bash

    # Delete an environment from zendev config, but leave files
    zendev drop ENVIRONMENT

    # Delete an environment and all files
    zendev drop --purge ENVIRONMENT
