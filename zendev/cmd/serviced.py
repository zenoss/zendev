from __future__ import absolute_import, print_function

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib3

import py.path
import requests

from ..devimage import DevImage
from ..log import error, info
from ..utils import get_ip_address, get_tmux_name, rename_tmux_window


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Serviced(object):

    env = None
    proc = None

    def __init__(self, env, uiport=443):
        self.env = env
        self.serviced = self.env.gopath.join("bin/serviced").strpath
        self.uiport = uiport
        self.dev_image = DevImage(env)

    def get_zenoss_image(self, zenoss_image):
        if zenoss_image != "zendev/devimg":
            return zenoss_image
        return self.dev_image.get_image_name()

    def reset(self):
        info("Stopping any running serviced")
        subprocess.call(["sudo", "pkill", "serviced"])
        info("Killing any running containers")
        running = subprocess.check_output(["docker", "ps", "-q"])
        if running:
            subprocess.call(["docker", "kill"] + running.splitlines())
        info("Cleaning state")
        subprocess.call(
            "sudo umount -f %s/var/volumes/*" % self.env.servicedhome.strpath,
            shell=True,
        )
        subprocess.call(
            "sudo rm -rf %s/*" % self.env.servicedhome.strpath, shell=True
        )

    def start(self, root=False, arguments=None, image=None):
        devimg_name = self.get_zenoss_image(image)
        if not self.dev_image.image_exists(devimg_name):
            error(
                "You don't have the devimg built. "
                'Please run "zendev devimg" first.'
            )
            sys.exit(1)

        info("Starting serviced...")
        rename_tmux_window("serviced")
        args = []
        envvars = self.env.envvars()
        envvars["TZ"] = os.getenv("TZ", "UTC")
        envvars["SERVICED_MASTER"] = os.getenv("SERVICED_MASTER", "1")
        envvars["SERVICED_AGENT"] = os.getenv("SERVICED_AGENT", "1")
        envvars["SERVICED_ISVCS_OPENTSDB_USERNAME"] = os.getenv(
            "SERVICED_ISVCS_OPENTSDB_USERNAME", "zenoss"
        )
        envvars["SERVICED_ISVCS_OPENTSDB_PASSWD"] = os.getenv(
            "SERVICED_ISVCS_OPENTSDB_PASSWD", "zenoss"
        )
        if root:
            args.extend(["sudo", "-E"])
            args.extend("%s=%s" % x for x in envvars.items())

        args.extend([self.serviced])
        mounts = self.dev_image.get_mounts()
        for mount in mounts.items():
            args.extend(
                ["--mount", "%s,%s,%s" % (devimg_name, mount[0], mount[1])]
            )
        args.extend(
            [
                "--mount",
                "zendev/impact-devimg,%s,/mnt/src"
                % self.env.root.join("src/github.com/zenoss").strpath,
                "--uiport",
                ":%d" % self.uiport,
            ]
        )
        if arguments:
            args.extend(arguments)

        # In serviced 1.1 and later, use subcommand 'server' to
        # request serviced be started
        servicedVersion = str(subprocess.check_output(
            "%s version | awk '/^Version:/ { print $NF; exit }'"
            % self.serviced,
            shell=True,
        ).strip())
        if (
            not servicedVersion.startswith("1.0.")
            and servicedVersion != "1.1.0"
        ):
            args.extend(["--allow-loop-back", "true"])
        if not servicedVersion.startswith("1.0."):
            args.extend(["server"])

        # Make sure etc is present and contains copies of config files
        etc = self.env.servicedhome.ensure("etc", dir=True)
        pkg = self.env.servicedsrc.join("pkg")
        for filename in (
            "logconfig-server.yaml",
            "logconfig-cli.yaml",
            "logconfig-controller.yaml",
        ):
            source = pkg.join(filename)
            target = etc.join(filename)
            if not target.check():
                try:
                    source.copy(target)
                except Exception:
                    pass

        # Symlink in isvcs/resources
        isvcs = self.env.servicedhome.ensure("isvcs", dir=True)
        linkpath = isvcs.join("resources")
        if not linkpath.check(exists=True):
            linkpath.mksymlinkto(
                self.env.servicedsrc.join("isvcs", "resources")
            )

        # Symlink in the web UI
        web = self.env.servicedhome.ensure("share", "web", dir=True)
        linkpath = web.join("static")
        if not linkpath.check(exists=True):
            linkpath.mksymlinkto(
                self.env.servicedsrc.join("web", "ui", "build")
            )

        info("Running command: %s" % args)
        self.proc = subprocess.Popen(args)

    def is_ready(self):
        try:
            response = requests.get(
                "https://localhost:%d" % self.uiport, verify=False
            )
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
        info("Adding host %s" % host)
        hostid = None
        # give up after 60 seconds
        timeout = time.time() + 60
        err = None
        while not hostid and time.time() < timeout:
            time.sleep(1)
            process = subprocess.Popen(
                [
                    "sudo",
                    "-E",
                    "SERVICED_HOME=%s" % self.env.servicedhome.strpath,
                    self.serviced,
                    "host",
                    "add",
                    "--register",
                    host,
                    pool,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = process.communicate()
            if out:
                ahostid = out.splitlines()[-1].strip()
                process = subprocess.Popen(
                    [self.serviced, "host", "list", ahostid],
                    stdout=subprocess.PIPE,
                )
                out, err = process.communicate()
                if ahostid in out:
                    hostid = ahostid.decode("utf-8")
                    info(
                        "Added hostid %s for host %s  pool %s"
                        % (hostid, host, pool)
                    )
            elif err:
                for line in err.split(b"\n"):
                    match = re.match(b"host already exists: (\\w+)", line)
                    if match:
                        hostid = match.group(1)
                        break

        if time.time() >= timeout:
            error(
                "Gave up trying to add host %s due to error: %s" % (host, err)
            )

    def get_hosts(self):
        process = subprocess.Popen(
            [
                "sudo",
                "-E",
                "SERVICED_HOME=%s" % self.env.servicedhome.strpath,
                self.serviced,
                "host",
                "list",
                "-v",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = process.communicate()
        if out:
            return json.loads(out.strip())
        else:
            if not err.startswith(b"no hosts found"):
                error(err)
            return []

    def deploy(
        self, template, pool="default", svcname="HBase", noAutoAssignIpFlag=""
    ):
        info("Deploying template")
        deploy_command = [self.serviced, "template", "deploy"]
        if noAutoAssignIpFlag != "":
            deploy_command.append(noAutoAssignIpFlag)
        deploy_command.append(template)
        deploy_command.append(pool)
        deploy_command.append(svcname)
        time.sleep(1)
        subprocess.call(deploy_command)
        info("Deployed templates:")
        subprocess.call([self.serviced, "template", "list"])

    def remove_catalogservice(self, services, svc):
        if svc["Name"] and svc["Name"] == "zencatalogservice":
            services.remove(svc)
            info("Removed zencatalogservice from resmgr template")
            return

        if (
            svc["HealthChecks"]
            and "catalogservice_answering" in svc["HealthChecks"]
        ):
            svc["HealthChecks"].pop("catalogservice_answering", None)
        if svc["Prereqs"]:
            for prereq in svc["Prereqs"]:
                if prereq["Name"] == "zencatalogservice response":
                    svc["Prereqs"].remove(prereq)

    def remove_otsdb_bigtable(self, services, svc):
        if svc["Name"] and svc["Name"] in (
            "reader-bigtable",
            "writer-bigtable",
        ):
            services.remove(svc)
            info("Removed %s from resmgr template" % svc["Name"])
            return

    def zope_debug(self, services, svc):
        if svc["Name"] and svc["Name"] == "Zope":
            info("Set Zope to debug in template")
            svc["Command"] = svc["Command"].replace("runzope", "zopectl fg")

            if svc["HealthChecks"]:
                for _, hc in list(svc["HealthChecks"].items()):
                    if "runzope" in hc["Script"]:
                        hc["Script"] = hc["Script"].replace(
                            "runzope", "zopectl"
                        )

    def zproxy_debug(self, services, svc):
        title = svc.get("Title", None)
        if title and title.lower() == "zproxy":
            configs = svc.get("ConfigFiles", {})
            config = configs.get(
                "/opt/zenoss/zproxy/conf/zproxy-nginx.conf", None
            )
            if config:
                config["Content"] = config["Content"].replace(
                    "pagespeed on", "pagespeed off"
                )
                info("Disabled pagespeed in zproxy template")

    def remove_auth0_vars(self, services, svc):
        if svc["Name"] and svc["Name"] == "Zenoss.cse":
            for var in (
                "auth0-audience",
                "auth0-emailkey",
                "auth0-tenant",
                "auth0-tenantkey",
                "auth0-whitelist",
            ):
                key = "global.conf.%s" % var
                if svc["Context"].get(key, None):
                    svc["Context"][key] = ""

    def walk_services(self, services, visitor):
        if not services:
            return

        for svc in services:
            visitor(services, svc)
            self.walk_services(svc["Services"], visitor)

    def get_template_path(self, template=None):
        if template is None:
            tplpath = self.zenoss_service_dir.join("services", "Zenoss.core")
        else:
            tentative = py.path.local(template)
            if tentative.exists():
                tplpath = tentative
            else:
                tplpath = self.zenoss_service_dir.join("services", template)
        return tplpath

    @property
    def zenoss_service_dir(self):
        return self.env.srcroot.join("github.com/zenoss/zenoss-service/")

    def compile_template(self, template, image):
        tplpath = self.get_template_path(template).strpath
        info("Compiling template %s" % tplpath)
        mk_template_cmd = self.zenoss_service_dir.join("make_template.sh")
        popenArgs = [mk_template_cmd.strpath, tplpath]
        proc = subprocess.Popen(
            popenArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()

        if proc.returncode:
            error(
                "Failed to compile template %s with return code %i\n %s"
                % (template, proc.returncode, stderr)
            )
            return

        info("Compiled new template")

        compiled = json.loads(stdout)
        self.walk_services(compiled["Services"], self.zope_debug)
        # disable pagespeed in zproxy to avoid
        # obfuscating javascript
        self.walk_services(compiled["Services"], self.zproxy_debug)
        if template and (
            "ucspm" in template
            or "resmgr" in template
            or "nfvimon" in template
        ):
            self.walk_services(
                compiled["Services"], self.remove_catalogservice
            )
        self.walk_services(compiled["Services"], self.remove_otsdb_bigtable)

        self.walk_services(compiled["Services"], self.remove_auth0_vars)

        stdout = json.dumps(
            compiled, sort_keys=True, indent=4, separators=(",", ": ")
        )
        return stdout

    def add_template(self, template=None):
        info("Adding template")
        addtpl = subprocess.Popen(
            [self.serviced, "template", "add"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        tplid, _ = addtpl.communicate(template.encode("utf-8"))
        tplid = tplid.strip()
        info("Added template %s" % tplid)
        return tplid

    def startall(self):
        p = subprocess.Popen(
            "%s service list | awk '/Zenoss/ {print $2; exit}'"
            % self.serviced,
            shell=True,
            stdout=subprocess.PIPE,
        )
        svcid, stderr = p.communicate()
        subprocess.call([self.serviced, "service", "start", svcid.strip()])

    MERGED_TEMPLATE_SUFFIX = "_with_modules"

    def add_template_module(self, baseTemplate, modules, moduleDir, image):
        baseTemplatePath = self.get_template_path(baseTemplate)
        if baseTemplatePath.check(dir=True):
            info("Using base template: {0} ".format(baseTemplatePath))
        else:
            raise Exception(
                "Cannot locate base template {} ".format(baseTemplatePath)
            )
        info("With additional services: {}".format(modules))

        modHash = hash(tuple(modules))
        tplName = baseTemplate + self.MERGED_TEMPLATE_SUFFIX
        tplHash = tplName + "_{}_".format(str(modHash))
        temppath = self.env.zenhome.join(".zentemplate").ensure(dir=True)

        # Create a temporary dir to hold the merged template. Three older
        # dir versions are kept, with the oldest ones removed as necessary.
        # The module hash helps identify the merged template as being
        # applicable to the specific combination of additional services.
        tplroot = temppath.make_numbered_dir(
            prefix=tplHash, rootdir=temppath, keep=3
        )
        tpldir = tplroot.join(tplName).ensure(dir=True)
        info("Creating merged template: {}".format(tpldir))

        tplReadme = tplroot.join("Contents")

        with tplReadme.open(mode="w") as f:
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
    old_name = get_tmux_name()
    timeout = 600
    environ = env()
    _serviced = Serviced(environ, args.uiport)
    if args.reset:
        _serviced.reset()
    if args.arguments and args.arguments[0] == "--":
        args.arguments = args.arguments[1:]

    if not _serviced.is_ready():
        _serviced.start(not args.no_root, args.arguments, args.image)
    try:
        wait_for_ready = not args.skip_ready_wait
        while wait_for_ready and not _serviced.is_ready():
            if not timeout:
                error("Timed out waiting for serviced!")
                sys.exit(1)
            # log every 5 attempts
            if not timeout % 5:
                info("Waiting for serviced to be ready")
            time.sleep(1)
            timeout -= 1

        if wait_for_ready:
            info("serviced is ready!")

        # opt_serviced/var/isvcs needs 755 perms
        var_isvcs = environ.servicedhome.join("var", "isvcs").__str__()
        if subprocess.call(["sudo", "chmod", "755", var_isvcs]):
            error(
                "Could not set appropriate permissions for %s. "
                "Continuing anyway." % var_isvcs
            )

        # Add host
        if "SERVICED_HOST_IP" in os.environ:
            host = os.environ.get("SERVICED_HOST_IP")
            ipAddr, port = host.split(":")
        else:
            ipAddr = get_ip_address() or "172.17.42.1"
            port = "4979"
        existing_hosts = _serviced.get_hosts()
        if all(host["IPAddr"] != ipAddr for host in existing_hosts):
            _serviced.add_host(host="{}:{}".format(ipAddr, port))

        if args.deploy or args.deploy_ana:

            if args.deploy_ana:
                args.template = environ.srcroot.join(
                    "/analytics/pkg/service/Zenoss.analytics"
                ).strpath

            deploymentId = "zendev-zenoss" if not args.deploy_ana else "ana"

            zenoss_image = _serviced.get_zenoss_image(args.image)
            tplid = None
            if args.module:
                tplid = _serviced.add_template_module(
                    args.template, args.module, args.module_dir, zenoss_image
                )
            else:
                # Assume that a file is compiled json;
                # directory needs to be compiled
                if py.path.local(args.template).isfile():
                    template = open(
                        py.path.local(args.template).strpath
                    ).read()
                else:
                    template = _serviced.compile_template(
                        args.template, zenoss_image
                    )

                if template:
                    tplid = _serviced.add_template(template)

            if tplid is None:
                error("Failed to deploy %s. Continuing anyway." % template)
            else:
                kwargs = dict(template=tplid, svcname=deploymentId)
                if args.no_auto_assign_ips:
                    kwargs["noAutoAssignIpFlag"] = "--manual-assign-ips"

                _serviced.deploy(**kwargs)

        if args.startall:
            _serviced.startall()
            info("Starting all services")
            # Join the subprocess

        # subtle hint that zenoss is ready to use
        print(
            r"""
 __________ _   _ ____  _______     __
|__  / ____| \ | |  _ \| ____\ \   / /
  / /|  _| |  \| | | | |  _|  \ \ / /
 / /_| |___| |\  | |_| | |___  \ V /
/____|_____|_| \_|____/|_____|  \_/
 ____  _____ ____  _     _____   ____  __ _____ _   _ _____
|  _ \| ____|  _ \| |   / _ \ \ / /  \/  | ____| \ | |_   _|
| | | |  _| | |_) | |  | | | \ V /| |\/| |  _| |  \| | | |
| |_| | |___|  __/| |__| |_| || | | |  | | |___| |\  | | |
|____/|_____|_|   |_____\___/ |_| |_|  |_|_____|_| \_| |_|
  ____ ___  __  __ ____  _     _____ _____ _____
 / ___/ _ \|  \/  |  _ \| |   | ____|_   _| ____|
| |  | | | | |\/| | |_) | |   |  _|   | | |  _|
| |__| |_| | |  | |  __/| |___| |___  | | | |___
 \____\___/|_|  |_|_|   |_____|_____| |_| |_____|

              `-/+ossoo/:`
          -ohmmmdhhhhdmmmdo-
        -ymmddhyssssssshmmmmh/
       ommy.  `+ssssssssymmmmmy`
      ymmm:    .sssssssssmmmmmmh`
     /mmmmdo/:/ssssssssshmmmmmmmo
     ymmmmmmmmdyssssssydmmmmmmmmd
     hmmmmmmmmmmmddddmmmmmmmmmmmm
     ommmmmmmmmmmmmmmmmmmmmmmmmmy
     `dmmmmmmmmmmmmmmmmmmmmmmmmd.
      ymmmy+++dmmms++mmmmo+smmmh
     ommmd`  -mmmm` `mmmm` `dmmm+
   `-/smh.  `hmmmo  +mmmy   -dmmms
 /ssss:.`  `ymmmy  :mmmm-    .ym/-/o+/.
-ssssss`  -hmmmy`.-::/d/       ..ssssss`
 :oss+- .smmmmo`ossss+          `ossss+
    `://-:ymy- .ssssss`           .--`
   .ssssso`:    ./++/`
   .ssssso
    `:/:-
"""
        )
        _serviced.wait()
    except Exception:
        _serviced.stop()
        raise
    except (KeyboardInterrupt, SystemExit):
        _serviced.stop()
        sys.exit(0)
    finally:
        rename_tmux_window(old_name)


def attach(args, env):
    """Attach to the container of the named service."""
    old_name = get_tmux_name()
    cmd = "serviced service attach '%s'; stty sane" % args.specifier
    try:
        rename_tmux_window(args.specifier)
        subprocess.call(cmd, shell=True)
    finally:
        rename_tmux_window(old_name)


def devshell(args, env):
    """Start a shell with the import of the Zope service but no command."""
    env = env()
    _serviced = env.gopath.join("bin/serviced").strpath

    old_name = get_tmux_name()
    rename_tmux_window("devshell")

    if not args.root:
        command = "su - zenoss"
        if args.command:
            command += " -c '%s'" % " ".join(args.command)
    else:
        command = "" if not args.command else " ".join(args.command)

    devimg = Serviced(env).get_zenoss_image("zendev/devimg:%s" % env.name)

    m2 = py.path.local(os.path.expanduser("~")).ensure(".m2", dir=True)
    if args.docker:
        cmd = (
            "docker run --privileged --rm -w /opt/zenoss "
            "-v {serviced}:/serviced/serviced "
            "-v {src}:/mnt/src "
            "-v {zenhome}:/opt/zenoss "
            "-v {var}:/var/zenoss "
            "-v {m2}:/home/zenoss/.m2 "
            "-e TZ=America/Chicago "
            "-i -t {image} {command}"
        ).format(
            serviced=_serviced,
            src=env.root.join("src", "github.com", "zenoss").strpath,
            zenhome=env.root.join("zenhome").strpath,
            var=env.root.join("var_zenoss").strpath,
            m2=m2.strpath,
            image=devimg,
            command=command,
        )
    else:
        cmd = (
            "{serviced} service shell -i "
            "--mount {src},/mnt/src "
            "--mount {zenhome},/opt/zenoss "
            "--mount {var},/var/zenoss "
            "--mount {m2},/home/zenoss/.m2 "
            "'{service}' {command}"
        ).format(
            serviced=_serviced,
            src=env.root.join("src", "github.com", "zenoss").strpath,
            zenhome=env.root.join("zenhome").strpath,
            var=env.root.join("var_zenoss").strpath,
            m2=m2.strpath,
            service=args.service,
            command=command,
        )
    try:
        subprocess.call(cmd, shell=True)
    finally:
        rename_tmux_window(old_name)


def add_commands(subparsers):
    serviced_parser = subparsers.add_parser("serviced", help="Run serviced")
    serviced_parser.add_argument(
        "--deploy_ana",
        action="store_true",
        help="Add only analytics service definitions and deploy an instance",
    )
    serviced_parser.add_argument(
        "-d",
        "--deploy",
        action="store_true",
        help="Add Zenoss service definitions and deploy an instance",
    )
    serviced_parser.add_argument(
        "-a",
        "--startall",
        action="store_true",
        help="Start all services once deployed",
    )
    serviced_parser.add_argument(
        "-x",
        "--reset",
        action="store_true",
        help="Clean service state and kill running containers first",
    )
    serviced_parser.add_argument(
        "--template",
        help="Zenoss service template"
        " file to add or directory to compile and add",
        default=None,
    )
    serviced_parser.add_argument(
        "--image",
        help="Zenoss image to use when compiling template",
        default="zendev/devimg",
    )
    serviced_parser.add_argument(
        "--module",
        help="Additional service modules" " for the Zenoss service template",
        nargs="+",
        default=None,
    )
    serviced_parser.add_argument(
        "--module_dir",
        help="Directory for additional service modules",
        default=None,
    )
    serviced_parser.add_argument(
        "--no-root",
        dest="no_root",
        action="store_true",
        help="Don't run serviced as root",
    )
    serviced_parser.add_argument(
        "--no-auto-assign-ips",
        action="store_true",
        help="Do NOT auto-assign IP addresses to services requiring "
        "an IP address",
    )
    serviced_parser.add_argument(
        "--with-docker-registry",
        action="store_true",
        default=False,
        help="Use the internal docker registry (necessary for multihost)",
    )
    serviced_parser.add_argument(
        "--skip-ready-wait",
        action="store_true",
        default=False,
        help="don't wait for serviced to be ready",
    )
    serviced_parser.add_argument(
        "--cluster-master",
        action="store_true",
        default=False,
        help="run as master for multihost cluster",
    )
    serviced_parser.add_argument(
        "-u", "--uiport", type=int, default=443, help="UI port"
    )
    serviced_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    serviced_parser.set_defaults(functor=run_serviced)

    attach_parser = subparsers.add_parser(
        "attach", help="Attach to serviced container"
    )
    attach_parser.add_argument(
        "specifier",
        metavar="SERVICEID|SERVICENAME|DOCKERID",
        help="Attach to a container matching SERVICEID|SERVICENAME|DOCKERID "
        "in service instances",
    )
    attach_parser.set_defaults(functor=attach)

    devshell_parser = subparsers.add_parser(
        "devshell", help="Start a development shell"
    )
    devshell_parser.add_argument(
        "-d",
        "--docker",
        action="store_true",
        help="docker run instead of serviced shell",
    )
    devshell_parser.add_argument(
        "-s",
        "--service",
        default="zope",
        help="run serviced shell for service",
    )
    devshell_parser.add_argument(
        "--root",
        action="store_true",
        default=False,
        help="Run shell as root instead of zenoss",
    )
    devshell_parser.add_argument(
        "command", nargs=argparse.REMAINDER, metavar="COMMAND"
    )
    devshell_parser.set_defaults(functor=devshell)
