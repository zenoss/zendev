import argparse
import subprocess
import sys
import os


def check_devimg(env):
    """
    return the image repo/tag for devimg
    prefer the image for this environment if one exists; otherwise the latest
    exit the program with a warning if no image is available
    """
    for tag in (env.name, 'latest'):
        devimg = 'zendev/devimg:' + tag
        if subprocess.check_output(['docker', 'images', '-q', devimg]) != '':
            return devimg
    print >> sys.stderr, ("You don't have the devimg built. Please run"
                          " zendev devimg\" first.")
    sys.exit(1)

def get_mounts(env):
    """
    return a map of mount points in the form of
    OS-local-directory-name:container-local-directory-name
    """
    envvars = env.envvars()
    envvars['HOME'] = os.getenv('HOME')
    print "envvars=%s" % envvars
    mounts = {
        os.path.join(envvars["HOME"], ".m2"):           "/home/zenoss/.m2",
        env.root.join("zenhome").strpath:               "/opt/zenoss",
        env.var_zenoss.strpath:                         "/var/zenoss",
        env.root.join("src/github.com/zenoss").strpath: "/mnt/src"
    }
    return mounts

def test(args, env):
    cmd = ["docker", "run", "-i", "-t", "--rm"]
    if args.no_tty:
        cmd.remove("-t")

    env = env()
    mounts = get_mounts(env)
    for mount in mounts.iteritems():
        cmd.extend(["-v", "%s:%s" % mount])

    image = check_devimg(env)
    cmd.append(image)

    if args.interactive:
        cmd.append('bash')
    else:
        cmd.append("/opt/zenoss/install_scripts/starttests.sh")
        cmd.extend(args.arguments[1:])

    print "Using %s image." % image
    print "Calling Docker with the following:"
    print " ".join(cmd)
    return subprocess.call(cmd)


def add_commands(subparsers):
    test_parser = subparsers.add_parser('test', help="Run Zenoss product tests")

    test_parser.add_argument('-i', '--interactive', action="store_true",
            help="Start an interactive shell instead of running the test",
            default=False)
    test_parser.add_argument('-n', '--no-tty', action="store_true",
            help="Do not allocate a TTY",
            dest="no_tty",
            default=False)
    test_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    test_parser.set_defaults(functor=test)
