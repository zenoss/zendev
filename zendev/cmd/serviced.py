import argparse
import os
import sys
import subprocess
import tempfile
import time

import py.path
import requests


DEVSHELLSTARTUP = """
/serviced/serviced service proxy %s 0 sleep 9999999999999999999 &>/dev/null &
echo Welcome to the Zenoss Dev Shell!
/bin/setuser zenoss /bin/bash
exit
"""


class Serviced(object):

    env = None
    proc = None

    def __init__(self, env):
        self.env = env
        self.serviced = self.env._gopath.join("bin/serviced").strpath
        self.uiport = None

    @property
    def varpath(self):
        return self.env.root.ensure("var", dir=True).ensure("serviced",
                dir=True)

    def reset(self):
        print "Stopping any running serviced"
        subprocess.call(['sudo', 'pkill', 'serviced'])
        print "Killing any running containers"
        running = subprocess.check_output(["docker", "ps", "-q"])
        if running:
            subprocess.call(["docker", "kill"] + running.splitlines())
        print "Cleaning state"
        subprocess.call("sudo rm -rf %s" % self.varpath.strpath, shell=True)

    def start(self, root=False, uiport=443, arguments=None, registry=False):
        print "Starting serviced..."
        self.uiport = uiport
        args = []
        envvars = self.env.envvars()
        envvars['SERVICED_VARPATH'] = self.varpath.strpath
        if registry:
            envvars['SERVICED_REGISTRY'] = 'true'
        if root:
            args.extend(["sudo", "-E"])
            args.extend("%s=%s" % x for x in envvars.iteritems())
        args.extend([self.serviced, "-master", "-agent",
            "--mount", "zendev/devimg,%s,/home/zenoss/.m2" % py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True),
            "--mount", "zendev/devimg,%s,/opt/zenoss" % self.env.root.join("zenhome").strpath,
            "--mount", "zendev/devimg,%s,/mnt/src" % self.env.root.join("src").strpath,
            "--uiport", ":%d" % uiport,
        ])

        if arguments:
          args.extend( arguments)

        print "Running command:", args
        self.proc = subprocess.Popen(args)

    def is_ready(self):
        try:
            response = requests.get("http://localhost:%d" % self.uiport)
        except Exception:
            return False
        return response.status_code == 200

    def wait(self):
        if self.proc is not None:
            sys.exit(self.proc.wait())

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except OSError:
                # We can't kill it. Likely ran as root. 
                # Let's assume it'll die on its own.
                pass

    def add_host(self, host="172.17.42.1:4979", pool="default"):
        subprocess.call([self.serviced, "host","add", host, pool])

    def deploy(self, template, pool="default", svcname="HBase",
            noAutoAssignIpFlag=""):
        print "Deploying template"
        deploy_command = [self.serviced, "template", "deploy"]
        if noAutoAssignIpFlag != "":
            deploy_command.append(noAutoAssignIpFlag)
        deploy_command.append(template)
        deploy_command.append(pool)
        deploy_command.append(svcname)
        time.sleep(1)
        subprocess.call(deploy_command)

    def add_template(self):
        print "Adding template"
        tpldir = self.env.buildroot.join("services/Zenoss.core").strpath
        proc = subprocess.Popen([self.serviced, "template", "compile",
            "--map=zenoss/zenoss5x,zendev/devimg", tpldir],
            stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        print "Compiled new template"
        addtpl = subprocess.Popen([self.serviced, "template", "add"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        tplid, _ = addtpl.communicate(stdout)
        tplid = tplid.strip()
        print "Added template", tplid
        return tplid

    def startall(self):
        p = subprocess.Popen("%s service list | awk '/Zenoss/ {print $2; exit}'" % self.serviced,
                shell=True, stdout=subprocess.PIPE)
        svcid, stderr = p.communicate()
        subprocess.call([self.serviced, "service", "start", svcid.strip()])


def run_serviced(args, env):
    timeout = 60
    _serviced = Serviced(env())
    if args.reset:
        _serviced.reset()
    if args.arguments and args.arguments[0] == '--':
        args.arguments = args.arguments[1:]
    if args.root:
        print >> sys.stderr, "--root is deprecated, as it is now the default. See --no-root."
    _serviced.start(not args.no_root, args.uiport, args.arguments, registry=args.with_docker_registry)
    try:
        while not _serviced.is_ready():
            if not timeout:
                print "Timed out waiting for serviced!"
                sys.exit(1)
            print "Not ready yet. Checking again in 1 second."
            time.sleep(1)
            timeout -= 1
        print "serviced is ready!"
        if args.deploy:
            _serviced.add_host()
            tplid = _serviced.add_template()
            if args.no_auto_assign_ips:
                _serviced.deploy(template=tplid, noAutoAssignIpFlag="--manual-assign-ips")
            else:
                _serviced.deploy(tplid)
        if args.startall:
            _serviced.startall()
            # Join the subprocess
        _serviced.wait()
    except Exception:
        _serviced.stop()
        raise
    except (KeyboardInterrupt, SystemExit):
        _serviced.stop()
        sys.exit(0)


def attach(args, env):
    subprocess.call("serviced service attach '%s'; stty sane" % args.specifier, shell=True)


def devshell(args, env):
    """
    Start up a shell with the imports of the Zope service but no command.
    """
    env = env()
    _serviced = env._gopath.join("src/github.com/control-center/serviced/serviced").strpath
    zopesvc = subprocess.check_output(
        "%s service list | grep -i %s | awk {'print $2;exit'}" % (_serviced, args.svcname),
        shell=True).strip()

    m2 = py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True)
    with tempfile.NamedTemporaryFile() as f:
        f.write(DEVSHELLSTARTUP % zopesvc)
        f.flush()
        cmd = "docker run --privileged --rm -w /opt/zenoss -v %s:/.bashrc -v %s:/serviced/serviced -v %s/src:/mnt/src -v %s:/opt/zenoss -v %s:/home/zenoss/.m2 -i -t zendev/devimg /bin/bash" % (
            f.name,
            _serviced,
            env.root.strpath,
            env.root.join("zenhome").strpath,
            m2.strpath)
        subprocess.call(cmd, shell=True)


def add_commands(subparsers):
    serviced_parser = subparsers.add_parser('serviced')
    serviced_parser.add_argument('-r', '--root', action='store_true',
                                 help="Run serviced as root (DEPRECATED. Currently ignored; see --no-root)")
    serviced_parser.add_argument('-d', '--deploy', action='store_true',
                                 help="Add Zenoss service definitions and deploy an instance")
    serviced_parser.add_argument('-a', '--startall', action='store_true',
                                 help="Start all services once deployed")
    serviced_parser.add_argument('-x', '--reset', action='store_true',
                                 help="Clean service state and kill running containers first")
    serviced_parser.add_argument('--no-root', dest="no_root",
                                 action='store_true', help="Don't run serviced as root")
    serviced_parser.add_argument('--no-auto-assign-ips', action='store_true',
                                 help="Do NOT auto-assign IP addresses to services requiring an IP address")
    serviced_parser.add_argument('--with-docker-registry', action='store_true', default=False,
                                 help="Use the internal docker registry (necessary for multihost)")
    serviced_parser.add_argument('-u', '--uiport', type=int, default=443,
                                 help="UI port")
    serviced_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    serviced_parser.set_defaults(functor=run_serviced)

    attach_parser = subparsers.add_parser('attach')
    attach_parser.add_argument('specifier', metavar="SERVICEID|SERVICENAME|DOCKERID",
                               help="Attach to a container matching SERVICEID|SERVICENAME|DOCKERID in service instances")
    attach_parser.set_defaults(functor=attach)

    devshell_parser = subparsers.add_parser('devshell')
    devshell_parser.add_argument('svcname', nargs="?", default="zope")
    devshell_parser.set_defaults(functor=devshell)

