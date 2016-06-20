import argparse
import json
import os
import sys
import subprocess
import tempfile
import time
import re

import py.path
import requests
from vagrantManager import VagrantManager
from ..log import info
from ..utils import get_ip_address

class Serviced(object):

    env = None
    proc = None

    def __init__(self, env):
        self.env = env
        self.serviced = self.env._gopath.join("bin/serviced").strpath
        self.uiport = None

    def get_zenoss_image(self, zenoss_image):
        if zenoss_image != 'zendev/devimg':
            return zenoss_image
        zenoss_image += ':' + self.env.name
        image_id = subprocess.check_output(['docker', 'images', '-q', zenoss_image])
        if image_id:
            return zenoss_image
        return 'zendev/devimg:latest'

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
        subprocess.call("sudo rm -rf %s/*" % self.varpath.strpath, shell=True)

    def start(self, root=False, uiport=443, arguments=None, registry=False, cluster_master=False, image=None):
        print "Starting serviced..."
        self.uiport = uiport
        args = []
        envvars = self.env.envvars()
        envvars['SERVICED_VARPATH'] = self.varpath.strpath
        envvars['TZ'] = os.getenv('TZ', 'UTC')
        envvars['SERVICED_MASTER'] = os.getenv('SERVICED_MASTER', '1')
        envvars['SERVICED_AGENT'] = os.getenv('SERVICED_AGENT', '1')
        if registry or cluster_master:
            envvars['SERVICED_REGISTRY'] = 'true'
        if cluster_master:
            envvars['SERVICED_OUTBOUND_IP'] = VagrantManager.VIRTUALBOX_HOST_IP
        if root:
            args.extend(["sudo", "-E"])
            args.extend("%s=%s" % x for x in envvars.iteritems())
        devimg = self.get_zenoss_image(image)
        args.extend([self.serviced,
            "--mount", "%s,%s,/home/zenoss/.m2" % (devimg, py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True)),
            "--mount", "%s,%s,/opt/zenoss" % (devimg, self.env.root.join("zenhome").strpath),
            "--mount", "%s,%s,/mnt/src" % (devimg, self.env.root.join("src").strpath),
            "--mount", "%s,%s,/var/zenoss" % (devimg, self.env.var_zenoss.strpath),
            "--mount", "zendev/impact-devimg,%s,/mnt/src" % self.env.root.join("src").strpath,
            "--uiport", ":%d" % uiport,
        ])
        if arguments:
          args.extend(arguments)
        # In serviced 1.1 and later, use subcommand 'server' to specifically request serviced be started
        servicedVersion = subprocess.check_output("%s version | awk '/^Version:/ { print $NF; exit }'" % self.serviced, shell=True).strip()
        if not servicedVersion.startswith("1.0.") and servicedVersion != "1.1.0":
            args.extend(["--allow-loop-back", "true"])
        if not servicedVersion.startswith("1.0."):
            args.extend(["server"])

        print "Running command:", args
        self.proc = subprocess.Popen(args)

    def is_ready(self):
        try:
            response = requests.get("https://localhost:%d" % self.uiport, verify=False)
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
        hostid = None
        while not hostid:
            time.sleep(1)
            process = subprocess.Popen([self.serviced, "host","add", host, pool], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            if out:
                ahostid = out.rstrip()
                process = subprocess.Popen([self.serviced, "host", "list", ahostid], stdout=subprocess.PIPE)
                out, _ = process.communicate()
                if ahostid in out:
                    hostid = ahostid
                    print "Added hostid %s for host %s  pool %s" % (hostid, host, pool)
            elif err:
                match = re.match("host already exists: (\\w+)", err)
                if match:
                    hostid = match.group(1)

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
        print "Deployed templates:"
        subprocess.call([self.serviced, "template", "list"])

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

    def get_template_path(self, template=None):
        tplpath = None
        if template is None:
            tplpath = self.env.srcroot.join("service/services/Zenoss.core")
        else:
            tentative = py.path.local(template)
            if tentative.exists():
                tplpath = tentative
            else:
                tplpath = self.env.srcroot.join("service/services/" + template)
        return tplpath

    def compile_template(self, template, image):
        tplpath = self.get_template_path(template).strpath
        print "Compiling template", tplpath
        serviceMakefile = self.env.srcroot.join("service/makefile")
        hbaseVersion = subprocess.check_output("awk -F= '/^hbase_VERSION/ { print $NF }' %s | sed 's/^\s*//g;s/\s*$//g'" % serviceMakefile, shell=True).strip()
        hdfsVersion = subprocess.check_output("awk -F= '/^hdfs_VERSION/ { print $NF }' %s | sed 's/^\s*//g;s/\s*$//g'" % serviceMakefile, shell=True).strip()
        opentsdbVersion = subprocess.check_output("awk -F= '/^opentsdb_VERSION/ { print $NF }' %s | sed 's/^\s*//g;s/\s*$//g'" % serviceMakefile, shell=True).strip()
        print "Detected hbase version in makefile is %s" % hbaseVersion
        print "Detected opentsdb version in makefile is %s" % opentsdbVersion
        if hbaseVersion == "" or opentsdbVersion == "":
            raise Exception("Unable to get opentsdb/hbase tags from services makefile")
        proc = subprocess.Popen([self.serviced, "template", "compile",
            "--map=zenoss/zenoss5x,%s" % image,
            "--map=zenoss/hbase:xx,zenoss/hbase:%s" % hbaseVersion,
            "--map=zenoss/hdfs:xx,zenoss/hdfs:%s" % hdfsVersion,
            "--map=zenoss/opentsdb:xx,zenoss/opentsdb:%s" % opentsdbVersion, tplpath],
            stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        print "Compiled new template"

        compiled=json.loads(stdout);
        self.walk_services(compiled['Services'], self.zope_debug)
        if template and ('ucspm' in template or 'resmgr' in template or 'nfvimon' in template):
            self.walk_services(compiled['Services'], self.remove_catalogservice)
        stdout = json.dumps(compiled, sort_keys=True, indent=4, separators=(',', ': '))
        return stdout

    def add_template(self, template=None):
        print "Adding template"
        addtpl = subprocess.Popen([self.serviced, "template", "add"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        tplid, _ = addtpl.communicate(template)
        tplid = tplid.strip()
        print "Added template", tplid
        return tplid

    def startall(self):
        p = subprocess.Popen("%s service list | awk '/Zenoss/ {print $2; exit}'" % self.serviced,
                shell=True, stdout=subprocess.PIPE)
        svcid, stderr = p.communicate()
        subprocess.call([self.serviced, "service", "start", svcid.strip()])

    MERGED_TEMPLATE_SUFFIX="_with_modules"

    def add_template_module(self, baseTemplate, modules, moduleDir, image):
        baseTemplatePath = self.get_template_path(baseTemplate)
        if baseTemplatePath.check(dir=True):
            info("Using base template: {0} ".format(baseTemplatePath))
        else:
            raise Exception("Cannot locate base template {} ".format(baseTemplatePath))
        info("With additional services: {}".format(modules))

        modHash = hash(tuple(modules))
        tplName = baseTemplate + self.MERGED_TEMPLATE_SUFFIX
        tplHash = tplName + "_{}_".format(str(modHash))
        temppath = self.env.zenhome.join('.zentemplate').ensure(dir=True)

        # Create a temporary dir to hold the merged template. 3 older dir versions are kept,
        # with the oldest ones removed as necessary. The module hash helps identify the merged
        # template as being applicable to the specific combination of additional services.
        tplroot = temppath.make_numbered_dir(prefix=tplHash, rootdir=temppath, keep=3)
        tpldir = tplroot.join(tplName).ensure(dir=True)
        info("Creating merged template: {}".format(tpldir))

        tplReadme = tplroot.join("Contents")

        with tplReadme.open(mode='w') as f:
            f.write("Adding base template: {0}\n".format(baseTemplatePath))
            baseTemplatePath.copy(tpldir)
            for mod in modules:
                mdir = py.path.local(moduleDir).join(mod)
                if mdir.check(dir=True):
                    modMsg = "Adding service: {0} \n".format(mdir)
                    f.write(modMsg)
                    info(modMsg)
                    targetdir = tpldir.join(mod).ensure(dir=True)
                    mdir.copy(targetdir)
                else:
                    raise Exception("Cannot locate module: {0} ".format(mdir))

        return self.add_template(self.compile_template(tpldir.strpath, image))


def run_serviced(args, env):
    timeout = 600
    _serviced = Serviced(env())
    if args.reset:
        _serviced.reset()
    if args.arguments and args.arguments[0] == '--':
        args.arguments = args.arguments[1:]
    if args.root:
        print >> sys.stderr, "--root is deprecated, as it is now the default. See --no-root."
    _serviced.start(not args.no_root, args.uiport, args.arguments, args.with_docker_registry,
            args.cluster_master, args.image)
    try:
        wait_for_ready = not args.skip_ready_wait
        while wait_for_ready and not _serviced.is_ready():
            if not timeout:
                print "Timed out waiting for serviced!"
                sys.exit(1)
            print "Not ready yet (countdown:%d). Checking again in 1 second." % timeout
            time.sleep(1)
            timeout -= 1
        if wait_for_ready:
            print "serviced is ready!"

        if args.deploy or args.deploy_ana:
            if 'SERVICED_HOST_IP' in os.environ:
                _serviced.add_host(host=os.environ.get('SERVICED_HOST_IP'))
            else:
                ipAddr = get_ip_address() or "172.17.42.1"
                _serviced.add_host(ipAddr + ":4979")

            if args.deploy_ana:
                args.template=env().srcroot.join('/analytics/pkg/service/Zenoss.analytics').strpath

            deploymentId = 'zendev-zenoss' if not args.deploy_ana else 'ana'

            zenoss_image = _serviced.get_zenoss_image(args.image)
            if args.module:
                tplid = _serviced.add_template_module(args.template,
                    args.module, args.module_dir, zenoss_image)
            else:
                # Assume that a file is compiled json; directory needs to be compiled
                if py.path.local(args.template).isfile():
                    template = open(py.path.local(args.template).strpath).read()
                else:
                    template = _serviced.compile_template(args.template, zenoss_image)
                tplid = _serviced.add_template(template)

            kwargs = dict(template=tplid, svcname=deploymentId )
            if args.no_auto_assign_ips:
                kwargs['noAutoAssignIpFlag'] = '--manual-assign-ips'

            _serviced.deploy(**kwargs)

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

    devimg = Serviced(env).get_zenoss_image('zendev/devimg')

    m2 = py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True)
    if args.docker:
        cmd = "docker run --privileged --rm -w /opt/zenoss -v %s:/serviced/serviced -v %s/src:/mnt/src -v %s:/opt/zenoss -v %s:/var/zenoss -v %s:/home/zenoss/.m2 -i -t %s %s" % (
            _serviced,
            env.root.strpath,
            env.root.join("zenhome").strpath,
            env.root.join("var_zenoss").strpath,
            m2.strpath,
            devimg,
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


def ServicesCompleter(prefix, **kwargs):
    cmd = "serviced service list --show-fields 'Inst, Name' | awk '$1 + 0 > 0 { print tolower($2) }'"
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, _ = p.communicate()
    prefix = prefix.lower()
    return (v for v in out.splitlines() if v.startswith(prefix))


def add_commands(subparsers):
    serviced_parser = subparsers.add_parser('serviced', help='Run serviced')
    serviced_parser.add_argument('-r', '--root', action='store_true',
                                 help="Run serviced as root (DEPRECATED. Currently ignored; see --no-root)")
    serviced_parser.add_argument('--deploy_ana', action='store_true',
                                 help="Add only analytics service definitions and deploy an instance")
    serviced_parser.add_argument('-d', '--deploy', action='store_true',
                                 help="Add Zenoss service definitions and deploy an instance")
    serviced_parser.add_argument('-a', '--startall', action='store_true',
                                 help="Start all services once deployed")
    serviced_parser.add_argument('-x', '--reset', action='store_true',
                                 help="Clean service state and kill running containers first")
    serviced_parser.add_argument('--template', help="Zenoss service template"
            " file to add or directory to compile and add", default=None)
    serviced_parser.add_argument('--image', help="Zenoss image to use when compiling template",
                                 default='zendev/devimg')
    serviced_parser.add_argument('--module', help="Additional service modules"
                                  " for the Zenoss service template",
                                 nargs='+', default=None)
    serviced_parser.add_argument('--module_dir', help="Directory for additional service modules", default=None)
    serviced_parser.add_argument('--no-root', dest="no_root",
                                 action='store_true', help="Don't run serviced as root")
    serviced_parser.add_argument('--no-auto-assign-ips', action='store_true',
                                 help="Do NOT auto-assign IP addresses to services requiring an IP address")
    serviced_parser.add_argument('--with-docker-registry', action='store_true', default=False,
                                 help="Use the internal docker registry (necessary for multihost)")
    serviced_parser.add_argument('--skip-ready-wait', action='store_true', default=False,
                                 help="don't wait for serviced to be ready")
    serviced_parser.add_argument('--cluster-master', action='store_true', default=False,
                                 help="run as master for multihost cluster")
    serviced_parser.add_argument('-u', '--uiport', type=int, default=443,
                                 help="UI port")
    serviced_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    serviced_parser.set_defaults(functor=run_serviced)

    attach_parser = subparsers.add_parser('attach', help='Attach to serviced container')
    attach_parser.add_argument('specifier', metavar="SERVICEID|SERVICENAME|DOCKERID",
                               help="Attach to a container matching SERVICEID|SERVICENAME|DOCKERID in service instances"
                               ).completer = ServicesCompleter
    attach_parser.set_defaults(functor=attach)

    devshell_parser = subparsers.add_parser('devshell', help='Start a development shell')
    devshell_parser.add_argument('-d', '--docker', action='store_true',
                                 help="docker run instead of serviced shell")
    devshell_parser.add_argument('-s', '--service', default='zope', help="run serviced shell for service")
    devshell_parser.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND')
    devshell_parser.set_defaults(functor=devshell)

