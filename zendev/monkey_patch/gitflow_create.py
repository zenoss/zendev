# Monkey-patch gitflow.branches.BranchManager.create.
#
# This fixes a bug in which we would check that the default_base is up-to-date
#  even when a non-default base is specified.


import gitflow.branches
from gitflow.exceptions import (NoSuchBranchError, BranchExistsError,
                                PrefixNotUniqueError, BaseNotOnBranch,
                                WorkdirIsDirtyError, BranchTypeExistsError,
                                TagExistsError, MergeError)

# This code is based on the corresponding code in gitflow v0.5.1
# https://github.com/htgoebel/gitflow
def create(self, name, base=None, fetch=False,
           must_be_on_default_base=False):
    """
    Creates a branch of the type that this manager manages and checks it
    out.

    :param name:
        The (short) name of the branch to create.

    :param base:
        The base commit or ref to base the branch off from.  If a base is
        not provided explicitly, the default base for this type of branch is
        used.  See also :meth:`default_base`.

    :param fetch:
        If set, update the local repo with remote changes prior to
        creating the new branch.

    :param must_be_on_default_base:
        If set, the `base` must be a valid commit on the branch
        manager `default_base`.

    :returns:
        The newly created :class:`git.refs.Head` reference.
    """
    gitflow = self.gitflow
    repo = gitflow.repo

    full_name = self.prefix + name
    if full_name in repo.branches:
        raise BranchExistsError(full_name)

    gitflow.require_no_merge_conflict()
    if gitflow.has_staged_commits():
        raise WorkdirIsDirtyError('Contains local changes checked into '
                                  'the index but not committed.')

    if base is None:
        base = self.default_base()
    elif must_be_on_default_base:
        if not gitflow.is_merged_into(base, self.default_base()):
            raise BaseNotOnBranch(base, self.default_base())

    # update the local repo with remote changes, if asked
    if fetch:
        # :fixme: Should this be really `fetch`, not `update`?
        # :fixme:  `fetch` does not change any refs, so it is quite
        # :fixme:  useless. But `update` would advance `develop` and
        # :fixme:  moan about required merges.
        # :fixme:  OTOH, `update` would also give new remote refs,
        # :fixme:  e.g. a remote branch with the same name.
        print "fetch", base
        gitflow.origin().fetch(base)

    # If the origin branch counterpart exists, assert that the
    # local branch isn't behind it (to avoid unnecessary rebasing).
    if gitflow.origin_name(base) in repo.refs:
        # :todo: rethink: check this only if base == default_base()?
        gitflow.require_branches_equal(
            gitflow.origin_name(base),
            base)

    # If there is a remote branch with the same name, use it
    remote_branch = None
    if gitflow.origin_name(full_name) in repo.refs:
        remote_branch = repo.refs[gitflow.origin_name(full_name)]
        if fetch:
            gitflow.origin().fetch(remote_branch.remote_head)
            # Base must be on the remote branch, too, to avoid conflicts
        if not gitflow.is_merged_into(base, remote_branch):
            raise BaseNotOnBranch(base, remote_branch)
            # base the new local branch on the remote on
        base = remote_branch

    branch = repo.create_head(full_name, base)
    branch.checkout()
    if remote_branch:
        branch.set_tracking_branch(remote_branch)
    return branch


gitflow.branches.BranchManager.create = create
