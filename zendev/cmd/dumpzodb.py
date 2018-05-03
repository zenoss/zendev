import subprocess

def dumpzodb(args, env):
    environ = env()
    cmdArgs = ['make']
    cmdArgs.append('dumpdb')
    cmdArgs.append("ZENDEV_ROOT=%s" % environ.root.strpath)
    cmdArgs.append("SRCROOT=%s" % environ.srcroot.strpath)
    cmdArgs.append('DEV_ENV=%s' % environ.name)

    if not args.gz:
        cmdArgs.append('ZENWIPE_ARGS=--xml')

    devimgSrcDir = environ.productAssembly.join("devimg")
    print "cd %s" % devimgSrcDir.strpath
    devimgSrcDir.chdir()
    print " ".join(cmdArgs)
    subprocess.check_call(cmdArgs)

def add_commands(subparsers):
    epilog = '''
    To dump clean, updated database files to Products/ZenModel/data,
    build a core devimg with:
    zendev devimg --clean
    and then run:
    zendev dump-zodb
    '''

    dumpzodb_parser = subparsers.add_parser('dump-zodb', help="Manage zodb", epilog=epilog)
    dumpzodb_parser.add_argument('-z', '--load-from-gz', action="store_true",
            help="Load data from the .gz file instead of the .xml files",
            dest="gz",
            default=False)
    dumpzodb_parser.set_defaults(functor=dumpzodb)
