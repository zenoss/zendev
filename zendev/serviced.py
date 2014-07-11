import os
import sys
import subprocess
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

    def reset(self):
        print "Stopping any running serviced"
        subprocess.call(['sudo', 'pkill', 'serviced'])
        print "Killing any running containers"
        running = subprocess.check_output(["docker", "ps", "-q"])
        if running:
            subprocess.call(["docker", "kill"] + running.splitlines())
        print "Cleaning state"
        subprocess.call("sudo rm -rf /tmp/serviced-*", shell=True)

    def start(self, root=False, uiport=443, arguments=None, registry=False):
        print "Starting serviced..."
        self.uiport = uiport
        args = []
        envvars = self.env.envvars()
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
