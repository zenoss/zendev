===============
Porting Changes
===============

zendev can help with porting changes between branches.  It can create a feature branch,
cherry-pick existing pull-requests or commits, and automatically create a pull-request
for the port.

Starting a port
---------------
``zendev port start`` creates a feature branch from the current branch and checks out
the new branch.

The command will fail if the working tree has changes or if the current branch is
not up to date with its upstream tracking branch.  Best practice is to perform a
``zendev restore`` before beginning work on a port.

The command's only argument is a name which is used to name the branch and is also
referred to in the pull-request comment.  Best practice is to name the port after the
ticket being worked; e.g., ZEN-1234

.. code-block:: bash

    # Create a branch for ticket ZEN-1234 from the support/5.0.x branch in the core repo
    cdz core
    zendev restore support/5.0.x
    zendev port start ZEN-1234


Cherry-picking a change
-----------------------
``zendev port cherry-pick`` will use ``git cherry-pick`` to move a fix to the current
branch.  It can cherry-pick individual commits or pull requests.  Pull requests are
specified by preceding the pull-request number with either "#" or "pull/"; e.g., *#12*
or *pull/12*.  (Note that the '#' character will need to be escaped to prevent the shell
from interpreting it as a comment.)

If the cherry-pick fails to merge, you will need to perform a manual merge and
``git cherry-pick --continue`` as described in the
`git cherry-pick documentation <http://git-scm.com/docs/git-cherry-pick>`_.

The commit message will include the pull-request or commit hash that was cherry-picked;
if the default is not satisfactory then the message may be modified by using
``git commit --amend``.

.. code-block:: bash

    # Cherry-pick a pull request.  (Note that the # is escaped)
    zendev port cherry-pick \#12

    # Cherry-pick a pull request - alternate form
    zendev port cherry-pick pull/12

    # Or cherry-pick an individual commit
    zendev port cherry-pick 3a592c68109d32280467a3b7b5f6a34800cb600c


Creating a pull-request
-----------------------
``zendev port pull-request`` will push the changes in the current branch to github
and create a pull request for the port.  The pull-request message will include
a list of all cherry-picks that were performed.  The pull-request message can be edited
on the pull-request's github page.

.. code-block:: bash

    # Create a pull request from the current branch
    zendev port pull-request


Porting in a single command
---------------------------
``zendev port do`` will create a feature branch from the current branch, cherry-pick the 
indicated fix, and submit the pull request in a single command

.. code-block:: bash

    # Port PR 12 to the current branch as part of ticket ZEN-1234
    zendev port do ZEN-1234 pull/12


Examples
--------
Cherry picking pull-request using separate commands

.. code-block:: bash

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ git checkout support/5.0.x
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


Cherry picking pull-request using a single command

.. code-block:: bash

    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ git checkout support/5.0.x
    jcrocker@jcrocker-dev:~/src/dev/src/test/TestProject$ zendev port do ZEN-123 \#8
    ==> Creating branch feature/ZEN-123 from support/5.0.x
    ==> Checkout feature/ZEN-123
    ==> Cherry picking commits into feature/ZEN-123
    ==> Creating pull request for branch "feature/ZEN-123" into "support/5.0.x"
    ==> 1 local commits in test/TestProject:feature/ZEN-123 need to be pushed.  Pushing...
    ==> Posting pull request
    ==> Pull Request: https://github.com/jafcrocker/TestProject/pull/14
