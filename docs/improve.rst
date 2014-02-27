================
Improving zendev
================
zendev is meant to be improved by everyone! Definitely not just Ian! Everything
helps. Please. I need to sleep.

Update zendev
~~~~~~~~~~~~~
Zendev should always be installed from a source checkout, in place. If you want
to update it, you can run:

.. code-block:: bash

    zendev selfupdate

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/zenoss/zendev/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything is open to whomever wants to
implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whomever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

zendev could always use more documentation. Docs live with the code, `in the zendev repository <https://github.com/zenoss/zendev/tree/develop/docs>`_.

1. Edit the documentation as you see fit. `Here's a reference for reStructuredText <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_.
2. Build the docs locally to test your edits (using Sphinx_).

.. code-block:: bash

    # Install Sphinx if not installed
    sudo pip install sphinx

    # Go to the root of the zendev tree
    cd ~/src/zendev

    # Build! This works best locally, because it will open a browser pointing
    # to your freshly built docs.
    make docs

Alternatively, you can build using a Docker image with Sphinx already
installed:

.. code-block:: bash

    # Go to the root of the zendev tree
    cd ~/src/zendev

    # Build. No fancy browser this time.
    make docker-docs

3. When satisfied, submit a pull request.
4. Once merged, `Jenkins <http://jenkins.zendev.org/job/zendev-docs/>`_ will
   build the docs and publish them to http://zenoss.github.io/zendev.

.. _Sphinx: http://sphinx-doc.org/

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/zenoss/zendev/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a collaborative project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `zendev` for local development.

1. Fork the `zendev repo on GitHub <https://github.com/zenoss/zendev>`_.
2. Clone your fork locally:

.. code-block:: bash

    git clone git@github.com:your_name_here/zendev.git

3. Install your local copy into a virtualenv_. 

.. code-block:: bash

    # Install virtualenvwrapper if you haven't already
    sudo pip install virtualenvwrapper
    echo "source $(which virtualenvwrapper.sh)" >> ~/.bashrc
    source $(which virtualenvwrapper.sh)

    # Create a virtualenv for zendev development on top of your cloned source
    mkvirtualenv zendev
    cd zendev
    pip install -e .

4. Create a branch for local development:

.. code-block:: bash

    git checkout -b name-of-your-bugfix-or-feature
   
Now you can make your changes locally.

5. Commit your changes and push your branch to GitHub:

.. code-block:: bash

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

6. Submit a pull request through the GitHub website.

.. _virtualenv: http://www.virtualenv.org/en/latest/
