import sys
import io
import subprocess


from ..log import error


def changelog(args, env):
    buf = io.StringIO()
    env = env()
    try:
        frommanifest = env.get_manifest(args.tag1)
    except Exception:
        error("%s is an invalid tag. See available tags with `zendev tag --list`" % args.tag1)
        sys.exit(1)
    try:
        tomanifest = env.get_manifest(args.tag2) if args.tag2 else env.manifest
    except Exception:
        error("%s is an invalid tag. See available tags with `zendev tag --list`" % args.tag2)
        sys.exit(1)
    for repo in env.repos():
        if repo.name == 'build': repo.name = '../build'
        ref1 = frommanifest._data['repos'].get(repo.name, {}).get('ref')
        ref2 = tomanifest._data['repos'].get(repo.name, {}).get('ref')
        if not ref1 or not ref2 or ref1 == ref2:
            continue
        result = repo.changelog(ref1, ref2)
        if result:
            buf.write(u"""
{repo_name} | {repo_url}
=============================================================================
{changelog}
""".format(repo_name=repo.name, repo_url=repo.url, changelog=result))
    full_log = buf.getvalue().strip()
    if sys.stdout.isatty():
        p = subprocess.Popen(["less"], stdin=subprocess.PIPE)
        p.communicate(full_log)
        p.wait()
    else:
        print full_log


def restore(args, env):
    env().restore(args.name)


def tag(args, env):
    if args.list:
        for tag in env().list_tags():
            print tag
    elif args.delete:
        if not args.name:
            error("Missing the name of a tag to delete")
            sys.exit(1)
        elif args.name == 'develop':
            error("You can't delete develop!")
            sys.exit(1)
        env().tag_delete(args.name)
    else:
        if not args.name:
            error("Missing the name of a tag to create")
            sys.exit(1)
        env().tag(args.name, args.strict, args.force, args.from_ref)


def add_commands(subparsers, completer):
    restore_parser = subparsers.add_parser('restore', help='Restore repository state to a tag')
    a = restore_parser.add_argument('name', metavar="NAME")
    a.completer = completer
    restore_parser.set_defaults(functor=restore)

    tag_parser = subparsers.add_parser('tag', help='Save the state of an environment to a tag')
    tag_parser.add_argument('--strict', action="store_true")
    tag_parser.add_argument('-l', '--list', action="store_true")
    tag_parser.add_argument('-f', '--force', action="store_true")
    tag_parser.add_argument('-D', '--delete', action="store_true")
    tag_parser.add_argument('-F', '--from', dest="from_ref", required=False)
    a = tag_parser.add_argument('name', metavar="NAME", nargs="?")
    a.completer = completer
    tag_parser.set_defaults(functor=tag)

    changelog_parser = subparsers.add_parser('changelog', help='Show difference between two tags')
    changelog_parser.add_argument('tag1', metavar="TAG").completer = completer
    changelog_parser.add_argument('tag2', metavar="TAG", nargs="?").completer = completer
    changelog_parser.set_defaults(functor=changelog)
