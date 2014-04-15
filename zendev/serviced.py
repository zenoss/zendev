import os
import sys
import subprocess

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

    def start(self, root, uiport, arguments=None):
        print "Starting serviced..."
        self.uiport = uiport
        args = []
        if root:
            args.extend(["sudo", "-E"])
            args.extend("%s=%s" % x for x in self.env.envvars().iteritems())
        args.extend([self.serviced, "-master", "-agent", 
            "-mount", "zendev/devimg,%s,/opt/zenoss" % self.env.root.join("zenhome").strpath,
            "-mount", "zendev/devimg,%s,/mnt/src" % self.env.root.join("src").strpath,
            "-uiport", ":%d" % uiport,
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
        subprocess.call([self.serviced, "add-host", host, pool])

    def deploy(self, template, pool="default", svcname="Zenoss", noAutoAssignIpFlag=""):
        deploy_command = [self.serviced, "deploy-template"]
        if noAutoAssignIpFlag != "":
            deploy_command.append(noAutoAssignIpFlag)
        deploy_command.append(template)
        deploy_command.append(pool)
        deploy_command.append(svcname)
        subprocess.call(deploy_command)

    def add_template(self):
        print "Adding template"
        tpldir = self.env.buildroot.join("services/Zenoss.core").strpath
        proc = subprocess.Popen([self.serviced, "compile-template",
            "-map=zenoss/zenoss5x,zendev/devimg", tpldir],
            stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        print "Compiled new template"
        addtpl = subprocess.Popen([self.serviced, "add-template", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        tplid, _ = addtpl.communicate(stdout)
        tplid = tplid.strip()
        print "Added template", tplid
        return tplid

    def startall(self):
        p = subprocess.Popen("%s services | awk '/Zenoss/ {print $2; exit}'" % self.serviced,
                shell=True, stdout=subprocess.PIPE)
        svcid, stderr = p.communicate()
        subprocess.call([self.serviced, "start-service", svcid.strip()])
