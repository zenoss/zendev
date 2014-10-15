=============
Running Tests
=============
zendev can run Zenoss and serviced tests for you, using ``zendev test``.

.. code-block:: bash

    usage: zendev test [-h] [-d] [-r] [-c] [-u] [-s] [-- ...]

    optional arguments:
      -h, --help            show this help message and exit
      -d, --zenoss-devimg   Run Zenoss unit tests using the current devimg
                            instance
      -r, --zenoss-resmgr   Build a resmgr image and run Zenoss unit tests
      -c, --zenoss-core     Build a core image and run Zenoss unit tests
      -u, --serviced        Run serviced unit tests
      -s, --serviced-smoke  Run serviced smoke tests


Zenoss Tests
============
Zenoss tests are executed using ``-d``, ``-r`` or ``-c``. If ``-d`` or
``--zenoss-devimg`` is specified, it will use your existing devimg to run the
tests. Otherwise, a Core or Resource Manager image will be built from your
current source to run the tests.

If you want to pass arguments to the underlying test runner, specify them after
a ``--``. e.g.:

.. code-block:: bash

    $ zendev test -d -- -m Products.ZenUtils


Control Center Tests
====================
Control Center tests are executed by specifying ``-u`` and/or ``-s``. Both are
executed on the current system and are a simple shortcut for changing to the
serviced directory and running ``make test`` or ``make smoketest``.

If you want to pass arguments to the underlying test runner, specify them after
a ``--``. e.g.:

.. code-block:: bash

    $ zendev test -u -- -v=3

This probably isn't very useful at the moment, since the underlying test runner
is our serviced makefile.


Running Multiple Tests
======================
It's entirely possible to run Zenoss tests, serviced unit tests and serviced
smoke tests in a single invocation. For example:

.. code-block:: bash

    $ zendev test -c -u -s

Keep in mind that passing arbitrary arguments to the test runners via ``--``
will almost certainly fail if Zenoss and serviced tests are both to be
executed.
