import argparse
import json
import os
import sys
import subprocess
import tempfile
import time

import py.path
import requests


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
        envvars['TZ'] = 'UTC'
        envvars['SERVICED_MASTER'] = os.getenv('SERVICED_MASTER', '1')
        envvars['SERVICED_AGENT'] = os.getenv('SERVICED_AGENT', '1')
        if registry:
            envvars['SERVICED_REGISTRY'] = 'true'
        if root:
            args.extend(["sudo", "-E"])
            args.extend("%s=%s" % x for x in envvars.iteritems())
        args.extend([self.serviced,
            "--mount", "zendev/devimg,%s,/home/zenoss/.m2" % py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True),
            "--mount", "zendev/devimg,%s,/opt/zenoss" % self.env.root.join("zenhome").strpath,
            "--mount", "zendev/devimg,%s,/mnt/src" % self.env.root.join("src").strpath,
            "--mount", "zendev/devimg,%s,/var/zenoss" % self.env.var_zenoss.strpath,
            "--mount", "/zenoss/impact-unstable:latest,%s,/mnt/src" % self.env.root.join("src").strpath,
            "--mount", "zendev/analytics-unstable:latest,%s,/opt/zenoss_analytics" % self.env.root.join("zen_ana_home").strpath,
            "--mount", "zendev/analytics-unstable:latest,%s,/mnt/src" % self.env.root.join("src/analytics").strpath,
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
        err = None
        while err != "":
            time.sleep(1)
            process = subprocess.Popen([self.serviced, "host","add", host, pool], stderr=subprocess.PIPE)
            _, err = process.communicate()

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

    def remove_catalogservice(self, services, svc):
        if svc['Name'] and svc['Name'] == 'zencatalogservice':
            services.remove(svc)
            print "Removed zencatalogservice from resmgr template"
            return

        if svc['HealthChecks'] and 'catalogservice_answering' in svc['HealthChecks']:
            svc['HealthChecks'].pop("catalogservice_answering", None)
        if svc['Prereqs']:
            for prereq in svc['Prereqs']:
                if prereq['Name'] == 'zencatalogservice response':
                    svc['Prereqs'].remove(prereq)

    def zope_debug(self, services, svc):
        if svc['Name'] and svc['Name'] == 'Zope':
            print "Set Zope to debug in template"
            svc['Command'] = svc['Command'].replace("runzope", "zopectl fg")

            if svc['HealthChecks']:
                for _, hc in list(svc['HealthChecks'].items()):
                    if "runzope" in hc['Script']:
                        hc['Script'] = hc['Script'].replace("runzope", "zopectl")

    def walk_services(self, services, visitor):
        if not services:
            return

        for svc in services:
            visitor(services, svc)
            self.walk_services(svc['Services'], visitor)

    def add_template(self, template=None):
        print "Adding template"
        if template is None:
            tplpath = self.env.srcroot.join("service/services/Zenoss.core").strpath
        else:
            tentative = py.path.local(template)
            if tentative.exists():
                tplpath = tentative.strpath
            else:
                tplpath = self.env.srcroot.join("service/services/" + template).strpath
        proc = subprocess.Popen([self.serviced, "template", "compile",
            "--map=zenoss/zenoss5x,zendev/devimg", tplpath],
            stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        print "Compiled new template"

        compiled=json.loads(stdout);
        self.walk_services(compiled['Services'], self.zope_debug)
        if template and ('ucspm' in template or 'resmgr' in template):
            self.walk_services(compiled['Services'], self.remove_catalogservice)
        stdout = json.dumps(compiled, sort_keys=True, indent=4, separators=(',', ': '))

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
    timeout = 600
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
            print "Not ready yet (countdown:%d). Checking again in 1 second." % timeout
            time.sleep(1)
            timeout -= 1
        def _deploy(args,svcname='HBase'):
            tplid = _serviced.add_template(args.template)
            if args.no_auto_assign_ips:
                _serviced.deploy(template=tplid, noAutoAssignIpFlag="--manual-assign-ips", svcname=svcname)
            else:
                _serviced.deploy(tplid, svcname=svcname)
        print "serviced is ready!"
        if args.deploy or args.deploy_ana or args.deploy_zenoss_ana:
            _serviced.add_host()
            if not args.deploy:
                args.template=env().srcroot.join('/analytics/pkg/service/Zenoss.analytics').strpath
                _deploy(args,'ana')
            if args.deploy_zenoss_ana:
                args.template=None
                _deploy(args)
            elif args.deploy:
                _deploy(args)
                
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
    _serviced = env._gopath.join("bin/serviced").strpath

    command = "su - zenoss"
    if args.command:
        command += " -c '%s'" % " ".join(args.command)

    m2 = py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True)
    if args.docker:
        cmd = "docker run --privileged --rm -w /opt/zenoss -v %s:/serviced/serviced -v %s/src:/mnt/src -v %s:/opt/zenoss -v %s:/var/zenoss -v %s:/home/zenoss/.m2 -i -t zendev/devimg %s" % (
            _serviced,
            env.root.strpath,
            env.root.join("zenhome").strpath,
            env.root.join("var_zenoss").strpath,
            m2.strpath,
            command
        )
    else:
        cmd = "%s service shell -i --mount %s/src,/mnt/src --mount %s,/opt/zenoss --mount %s,/var/zenoss --mount %s,/home/zenoss/.m2 '%s' %s" % (
            _serviced,
            env.root.strpath,
            env.root.join("zenhome").strpath,
            env.root.join("var_zenoss").strpath,
            m2.strpath,
            args.service,
            command
        )
    subprocess.call(cmd, shell=True)

def add_commands(subparsers):
    serviced_parser = subparsers.add_parser('serviced', help='Run serviced')
    serviced_parser.add_argument('-r', '--root', action='store_true',
                                 help="Run serviced as root (DEPRECATED. Currently ignored; see --no-root)")
    serviced_parser.add_argument('--deploy_zenoss_ana', action='store_true',
                                 help="Add Zenoss service definitions, analytics service definitions and deploy an instance")
    serviced_parser.add_argument('--deploy_ana', action='store_true',
                                 help="Add only analytics service definitions and deploy an instance")
    serviced_parser.add_argument('-d', '--deploy', action='store_true',
                                 help="Add Zenoss service definitions and deploy an instance")
    serviced_parser.add_argument('-a', '--startall', action='store_true',
                                 help="Start all services once deployed")
    serviced_parser.add_argument('-x', '--reset', action='store_true',
                                 help="Clean service state and kill running containers first")
    serviced_parser.add_argument('--template', help="Zenoss service template"
            " directory to compile and add", default=None)
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

    attach_parser = subparsers.add_parser('attach', help='Attach to serviced container')
    attach_parser.add_argument('specifier', metavar="SERVICEID|SERVICENAME|DOCKERID",
                               help="Attach to a container matching SERVICEID|SERVICENAME|DOCKERID in service instances")
    attach_parser.set_defaults(functor=attach)

    devshell_parser = subparsers.add_parser('devshell', help='Start a development shell')
    devshell_parser.add_argument('-d', '--docker', action='store_true',
                                 help="docker run instead of serviced shell")
    devshell_parser.add_argument('-s', '--service', default='zope', help="run serviced shell for service")
    devshell_parser.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND')
    devshell_parser.set_defaults(functor=devshell)

