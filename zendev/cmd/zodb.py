import argparse
import subprocess
import sys
import os

from serviced import devshell


def zodb(args, env):
    if not args.wipe and args.load is None and not args.dump:
        print "Nothing to do"
        return 0


    # Check service statuses
    zopeStatus = ""
    mariaStatus = ""
    rabbitStatus = ""
    cmd = ["serviced","service","status","--show-fields=Name,Status"]
    result = subprocess.check_output(cmd)
    for line in result.splitlines():
        parts = line.split()
        if len(parts) > 1:
            service = parts[-2].lower()
            status = parts[-1].lower()
            if service.endswith("zope"):
                zopeStatus = status
            elif service.endswith("mariadb"):
                mariaStatus = status
            elif service.endswith("rabbitmq"):
                rabbitStatus = status

    if (zopeStatus != "stopped"):
        print >> sys.stderr, ("Zope appears to be running.  Stop all services except mariadb and rabbit and try again")
        sys.exit(1)

    if args.load is not None:
        if (rabbitStatus != "running"):
            print >> sys.stderr, ("RabbitMQ is not running.  Start mariadb and rabbitMQ and try again")
            sys.exit(1)

    if args.wipe or args.load is not None:
        if (mariaStatus != "running"):
            print >> sys.stderr, ("Mariadb is not running.  Start mariadb and try again")
            sys.exit(1)


    # Wipe database
    if args.wipe:
        print "DESTROYING DATABASES"
        cmd=["serviced", "service", "attach", "mariadb", "su", "-", "zenoss", "-c", "/opt/zenoss/devimg/zenwipe.sh"]
        result = subprocess.call(cmd)
        if result != 0:
            print >> sys.stderr, ("zenwipe failed")
            return result

    # Load and/or dump database
    cmd = ["zendev", "devshell"]
    if args.load is not None:
        # Load database
        cmd.extend(["/opt/zenoss/devimg/zenreload.sh"])
        if args.load == "xml":
            cmd.append("--xml")
        if args.dump:
            cmd.append("&&")
        
    if args.dump:
        # Dump database
        cmd.extend(["cd", "/opt/zenoss/Products/ZenModel/data", "&&", "./exportXml.sh"])

    if len(cmd) > 0:
        print "Calling devshell with the following:"
        print " ".join(cmd)
        return subprocess.call(cmd)

    return 0


def add_commands(subparsers):
    epilog = '''
    To dump clean, updated database files to Products/ZenModel/data, 
    deploy a clean Zenoss.core, start mariadb and rabbit, and then use
    zendev zodb -w -l xml -d
    '''
    
    zodb_parser = subparsers.add_parser('zodb', help="Manage zodb", epilog=epilog)

    zodb_parser.add_argument('-w', '--wipe', action="store_true",
            help="Destroy and re-create empty databases",
            dest="wipe",
            default=False)
    zodb_parser.add_argument('-l', '--load',
            help="Re-load databases from XML or gz files",
            choices=['xml', 'gz'],
            dest="load")
    zodb_parser.add_argument('-d', '--dump', action="store_true",
            help="Dump new XML and gz files based on the current state of the database",
            dest="dump",
            default=False)

    zodb_parser.set_defaults(functor=zodb)
