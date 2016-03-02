import argparse
import py
import Queue
import re
from threading import Lock, Thread
import time
from collections import OrderedDict, namedtuple
from datetime import datetime
from httplib import HTTPException
from string import Formatter

import zendev.github as github
import zendev.log
from ..utils import repofilter, colored

_parse_date = lambda x: datetime.strptime(x,"%Y-%m-%dT%H:%M:%SZ")

_formats = OrderedDict((
    ("oneline",
        "{base.repo.name:<column=1>} {number:<column=2>} "
        "{user.login:<column=3>} {title}"),
    ("short",
        "{html_url:<color=yellow>}\n" 
        "User: {user.login}\n" 
        "{title:<indent=4>}\n"),
    ("medium",
        "{html_url:<color=yellow>}\n"
        "User: {user.login}\n"
        "Created: {created_at}\n"
        "{title:<indent=4>}\n"),
    ("full",
        "{html_url:<color=yellow>}\n"
        "User: {user.login}\n"
        "Base: {base.ref}\n"
        "Created: {created_at}\n"
        "{title:<indent=4>}\n\n"
        "{body:<indent=4>}\n"),
    ("fuller",
        "{html_url:<color=yellow>}\n"
        "User: {user.login}\n"
        "Base: {base.ref}\n"
        "Created: {created_at}\n"
        "Updated: {updated_at}\n"
        "{title:<indent=4>}\n\n"
        "{body:<indent=4>}\n"),
    ))


class DictionaryFormatter(Formatter):
    """ Formatter with custom behavior for formatting pull requests."""
    def __init__(self, *args, **kwargs):
        Formatter.__init__(self, *args, **kwargs)
        self.widths = {}

    def get_field(self, field_name, args, kwargs):
        """
        Treat field names of the form ".key" as dictionary lookups
        instead of attributes.  This allows natural specification of
        fields in the form "a.b.c" instead of "a[b][c]".  For legal
        PR field definitions see the response example in:
        https://developer.github.com/v3/pulls/#list-pull-requests
        """
        value = kwargs
        try:
            for key in field_name.split('.'):
                value = value[key]
        except TypeError:
            value = None
        return (value, field_name)

    _format_regexp = re.compile("(.*)<(.*)=(.*)>$")
    def format_field(self, value, format_spec):
        """ Add custom formatting  
        Custom formatter is a trailing "<func=val[,val]>" string in the 
        format specifier.  e.g., {html_url:<color=yellow>}
        """
        match = DictionaryFormatter._format_regexp.match(format_spec)
        if match:
            format_spec = match.group(1)
            func = getattr(self, '_custom_' + match.group(2))
            args = match.group(3).split(',')
        formatted = Formatter.format_field(self, value, format_spec)
        if match:
            formatted = func(formatted, *args)
        return formatted
    
    def needs_preprocess(self, format_string):
        def hasColumn(format_spec):
            match = DictionaryFormatter._format_regexp.match(format_spec or "")
            return match and match.group(2) == 'column'
        return any(hasColumn(i[2]) for i in self.parse(format_string))
    
    # Following routines are used for custom formatting operations
    def _custom_color(self, value, color):
        return colored(value, color)

    def _custom_indent(self, value, i, j=None):
        return int(i)*' ' + value.replace('\n', '\n'+int(j if j!=None else i)*' ')

    def _custom_column(self, value, key):
        self.widths[key] = max(len(value), self.widths.get(key, 0))
        return value.ljust(self.widths[key])


def _get_user():
    url = '/user'
    headers, response = github.perform('GET', url)
    try:
        status = headers['status']
        if status != '200 OK':
            raise HTTPException('Error getting ' + url + ' : ' + status)
        return response['login']
    except Exception as e:
        zendev.log.error(e)
        exit(1)


def _get_relevant_repos(args, env):
    if args.all_repos:
        _filter = repofilter()
    elif args.repo:
        _filter = repofilter(args.repo)
    else:
        cwd = py.path.local().strpath
        _filter = lambda x: cwd.startswith(x.path.strpath)
    repos = env().repos(_filter)
    return [i.reponame for i in repos]


def _get_format_string(args):
    if args.format:
        return args.format
    return _formats[args.pretty]


def _get_filter(args):
    filters = []
    if args.all_users:
        pass # don't apply a user filter
    elif args.user:
        filters.append(lambda x: x['user']['login'] in args.user)
    else:
        user = _get_user()
        filters.append(lambda x: x['user']['login'] == user)
    
    if args.after:
        filters.append(lambda x: _parse_date(x['created_at']) > args.after)
    if args.before:
        filters.append(lambda x: _parse_date(x['created_at']) < args.before)

    return lambda x: all(f(x) for f in filters)


def _get_sort_key(args):
    if args.sort == 'user':
        return lambda x: x['user']['login']
    if args.sort == 'repo':
        return lambda x: x['base']['repo']['name']
    if args.sort == 'created':
        return lambda x: _parse_date(x['created_at'])
    if args.sort == 'updated':
        return lambda x: _parse_date(x['updated_at'])


_link_regexp = re.compile('\s*<.*[\?&]page=([0-9]*).*>;\s*rel\s*=\s*"([^"]*)"')
def _get_last_page(headers):
    """Return the number of pages for the query extracted from the link field of the header
    Example: headers with a link value of the following string
    '<https://api.github.com/repositories/13422985/pulls?per_page=10&page=2>; rel="next",
     <https://api.github.com/repositories/13422985/pulls?per_page=10&page=9>; rel="last"'
        returns 9
    """
    links = headers.get('link','').split(',')
    for link in links:
        match = re.match(_link_regexp, link)
        if match and match.group(2) == 'last':
            return int(match.group(1))
    return 1

class Worker (Thread):
    """ Fetch a single page of pull requests in a separate thread """
    counter = 0
    _counter_lock = Lock()
    _logging_lock = Lock()

    def __init__(self, repo, page, context):
        super(self.__class__, self).__init__(name=repo + "_" + str(page),
                target=self._fetch,
                args=(repo, page, context))
        self.daemon=True

    def start(self):
        with Worker._counter_lock:
            Worker.counter += 1
        super(self.__class__, self).start()

    def _fetch(self, repo, page, context):
        try:
            url = '/repos/%s/pulls?state=%s&per_page=100&page=%d' % \
                (repo, context.state, page)
            if context.base:
                url += '&base=%s' % context.base
            headers, response = github.perform('GET', url)
            status = headers['status']
            if status != '200 OK':
                raise HTTPException('Error getting ' + url + ' : ' + status)
            if page == 1:
                last_page = _get_last_page(headers)
                for i in range(2, last_page + 1):
                    Worker(repo, i, context).start()
            for pr in filter(context.filter_func, response):
                context.output_queue.put(pr)
        except Exception as e:
            with Worker._logging_lock:
                zendev.log.error(e)
        finally:
            with Worker._counter_lock:
                Worker.counter -= 1


def pr_list(args, env):
    formatter = DictionaryFormatter()
    format_string = _get_format_string(args)
    filter_func = _get_filter(args)
    sort_key = _get_sort_key(args)
    reverse_sort = args.reverse

    pr_queue = Queue.Queue()
    context = namedtuple('WorkerContext', 'state base filter_func output_queue')(
            args.state, args.base, filter_func, pr_queue)
    for repo in _get_relevant_repos(args, env):
        Worker(repo, 1, context).start()

    # Wait for all of the workers to finish
    while Worker.counter > 0:
        time.sleep(0.1)

    pull_requests = []
    while not pr_queue.empty():
        pull_requests.append(pr_queue.get())

    pull_requests.sort(key=sort_key, reverse=reverse_sort)
    
    # This is a bit awkward.  If there is a column width in the format string,
    # we need to preprocess all of the records to find the longest string in
    # each column.  I found it to be easiest to have the format() routine 
    # have a side effect of accumulating the maximum width.  Not the most
    # elegant solution but good enough for now.
    if formatter.needs_preprocess(format_string):
        for pr in pull_requests:
            formatter.format(format_string, **pr)

    for pr in pull_requests:
        print formatter.format(format_string, **pr)


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a date of the form YYYY-MM-DD: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def add_commands(subparsers):
    pr_parser = subparsers.add_parser('pr', help='manage pull requests')
    pr_subparser = pr_parser.add_subparsers()
    ls_parser = pr_subparser.add_parser('ls',
            help='list pull requests for the current repo and current user')

    filter_group = ls_parser.add_argument_group("Filtering")
    filter_group.add_argument('-u', '--user', action='append',
            help='list only PRs for this user (can be multiple users)')
    filter_group.add_argument('-U', '--all-users', action='store_true',
            help='list PRs for all users')
    filter_group.add_argument('-r', '--repo', action='append',
            help='list only PRs for this repo (can be multiple repos)')
    filter_group.add_argument('-R', '--all-repos', action='store_true',
            help='list PRs for all repos in the manifest')
    filter_group.add_argument('--state', choices=('open', 'closed', 'all'),
            default='open',
            help='list only PRs with the given state (default=open)')
    filter_group.add_argument('--after', type=_valid_date,
            help='list only PRs created after this date (YYYY-MM-DD)')
    filter_group.add_argument('--before', type=_valid_date,
            help='list only PRs created before this date (YYYY-MM-DD)')
    filter_group.add_argument('--base',
            help='list only PRs targeting this branch')

    sort_group = ls_parser.add_argument_group("Sorting")
    sort_group.add_argument('--sort',
            choices=('created', 'user', 'repo', 'updated'),
            default='created',
            help='sort PRs by the specified field')
    sort_group.add_argument('--reverse', action='store_true',
            help='reverse order of sorted PRs')

    format_group = ls_parser.add_argument_group("Formatting")
    format_group.add_argument('--pretty', choices=_formats.keys(),
            default='short',
            help='select from predefined output formats (default=short)')
    format_group.add_argument('--format',
            help='specify output format string')
    ls_parser.set_defaults(functor=pr_list)
