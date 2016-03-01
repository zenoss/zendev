=============
Pull Requests
=============
zendev can help manage pull-requests on github.

Filtering Pull Requests
-----------------------

**Listing Pull-Requests**

``zendev pr ls`` will list all open PR's for the current user in the current repo.

**Listing Pull-Requests by User**

By default, ``zendev pr ls`` will list PR's for the current user.  The ``--all-users``
argument specifies that all users should be listed.  The ``--user`` argument can be 
used to specify a particular user; it can be repeated to specify more than one.

**Listing Pull-Requests by Repo**

By default, ``zendev pr ls`` will list PR's for the current repo.  The ``-all-repos``
argument specifies that all repos should be listed.  The ``--repo`` argument can be 
used to specify a particular repo; it can be repeated to specify more than one.  
When selecting repos with ``--repo``, zendev does a regex match on the argument to
find the repos on which to list.

**Listing Pull-Requests by Date**

The ``--before`` and ``--after`` arguements can be used to indicate a date range for 
listing pull requests.  The format for the dates is YYYY-MM-DD.


**Listing Pull-Requests by State**

The ``--state`` argument indicates which states (i.e., open closed, or all) for which
to list ull requests.  By default it will list open pull requests only.

Output Format
-------------

**Predefined formats**

The ``--pretty`` allows the specification of one of a number of predefined output formats.
Legal values in order of increasing verbosity are ``oneline``, ``short``, ``medium``, 
``full``, and ``fuller``.  The default is to use the ``short`` format.

- oneline

::

    serviced   2524 smousa Upgrade to go1.6

- short

::

    https://github.com/control-center/serviced/pull/2524
    User: smousa
        Upgrade to go1.6

- medium 

::

    https://github.com/control-center/serviced/pull/2524
    User: smousa
    Created: 2016-02-24T20:54:51Z
        Upgrade to go1.6

- full

::

    https://github.com/control-center/serviced/pull/2524
    User: smousa
    Created: 2016-02-24T20:54:51Z
        Upgrade to go1.6

        * Switched vendoring from GoDeps to Glide
        * Updated zookeeper client package (affects CC-1962) 
        * Fix to metrics/cache
        * Reverse sort of TLS keys
        * Removed (possible security?) issue with obsolete web terminal code

- fuller

::

    https://github.com/control-center/serviced/pull/2524
    User: smousa
    Created: 2016-02-24T20:54:51Z
    Updated: 2016-02-25T21:30:57Z
        Upgrade to go1.6

        * Switched vendoring from GoDeps to Glide
        * Updated zookeeper client package (affects CC-1962) 
        * Fix to metrics/cache
        * Reverse sort of TLS keys
        * Removed (possible security?) issue with obsolete web terminal code

**Custom Output Format**

A custom output format can be specified with th ``--format`` argument.  The 
format string is a `python format string
<https://docs.python.org/2/library/string.html#format-string-syntax>`_
which has been augmented slightly for this usage.  Replacement field names of
the form ".key" are treated as dictionary lookups instead of attribute 
references.  This allows natural specification of fields using the form "a.b.c"
instead of "a[b][c]".  The fields available to the format string are defined in the 
`Github API documentation
<https://developer.github.com/v3/pulls/#list-pull-requests>`_.
 
In addition to the standard format specification, special formatting operations 
are allowed.  To specify a custom operation, surround the operation and its
parameters in angle brackets (e.g., <operation=argument,argument>) and append 
it to the standard format specification string. The custom formats are 
``color``, which colorizes a field based on a color argument as defined in the 
`termcolor
<https://pypi.python.org/pypi/termcolor>`_ module, and ``indent``, 
which indents all lines of the field by the given amount.

For example, the definition for the ``full`` format is::

    "{html_url:<color=yellow>}\n" +
    "User: {user.login}\n" +
    "Created: {created_at}\n" +
    "{title:<indent=4>}\n\n" +
    "{body:<indent=4>}\n"),



