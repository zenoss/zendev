===============
Porting Changes
===============

zendev can help with porting changes between branches.  It can create a feature branch,
cherry-pick existing pull-requests or individual commits, and automatically create a
pull-request for the port.

Starting a port
---------------
``zendev port start`` creates a feature branch from the current branch and checks out
the new branch.  The command is given a name which is used to name the branch and is used
in the pull-request comment.  The best practice is to name the port after the ticket
being worked; e.g., ZEN-1234

.. code-block:: bash

    # Create a feature branch for ticket ZEN-1234 from the support/5.0.x branch
    git co support/5.0.x
    zendev port start ZEN-1234


Cherry-picking a change
----------------------
``zendev port cherry-pick`` will use ``git cherry-pick`` to move a fix to the current
branch.  It can cherry-pick individual commits or pull requests.  Pull requests are
specified by preceding the pull-request number with either '#' or 'pull/'; e.g., '#12'
or 'pull/12'.  If the cherry-pick fails to merge, you will need to perform a
manual merge and ``git cherry-pick --continue`` as described in the
`git cherry-pick documentation <http://git-scm.com/docs/git-cherry-pick>`_.  The commit
message will include the pull-request or commit hash that was cherry-picked.

.. code-block:: bash

    # Cherry pick a pull request.  (Note that the # is escaped)
    zendev port cherry-pick \#12

    # Cherry pick an individual commit
    zendev port cherry-pick 3a592c68109d32280467a3b7b5f6a34800cb600c


Creating a pull-request
-----------------------
``zendev port pull-request`` will push the changes in the current branch to github
and create a pull request for the port.  The pull-request message will include all
cherry-picks that were performed

.. code-block:: bash

    # Create a pull request from the current branch
    zendev port pull-request


Porting in a single command
---------------------------
``zendev port do`` will create the feature branch, cherry-pick the indicated fix, and
submit the pull request in a single command

.. code-block:: bash

    # Port PR 12 to the current branch as part of ticket ZEN-1234
    zendev port do ZEN-1234 \#12


Examples
--------
.. code-block:: bash

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ zendev port start ZEN-1234
    ==> Creating branch feature/ZEN-1234 from support/5.0.x
    ==> Checkout feature/ZEN-1234

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ zendev port cherry-pick \#8
    ==> Cherry picking commits into feature/ZEN-1234

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ zendev port pull-request
    ==> Creating pull request for branch "ZEN-1234" into "support/5.0.x"
    ==> 1 local commits in test/TestProject:feature/ZEN-1234 need to be pushed.Pushing...
    ==> Posting pull request
    ==> Pull Request: https://github.com/jafcrocker/TestProject/pull/11


.. code-block:: bash

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ zendev port try ZEN-123 \#8
    ==> Creating branch feature/ZEN-123 from support/5.0.x
    ==> Checkout feature/ZEN-123
    ==> Cherry picking commits into feature/ZEN-123
    ==> Creating pull request for branch "feature/ZEN-123" into "support/5.0.x"
    ==> 1 local commits in test/TestProject:feature/ZEN-123 need to be pushed.  Pushing...
    ==> Posting pull request
    ==> Pull Request: https://github.com/jafcrocker/TestProject/pull/14