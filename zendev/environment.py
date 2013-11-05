import py


_CFGDIR = '.zendev'


class NotInitialized(Exception): pass


def init_config_dir():
    """
    Create a config directory in PWD.

    :returns the config dir
    """
    cfgdir = py.path.local().ensure(_CFGDIR, dir=True)
    return cfgdir


def get_config_dir():
    for path in py.path.local().parts(reverse=True):
       cfgdir = path.join(_CFGDIR)
       if cfgdir.check():
           break
    else:
        raise NotInitialized()
    return cfgdir


class ZenDevEnvironment(object):

    _root = None

    def __init__(self):
        cfg_dir = get_config_dir()
        self._root = cfg_dir.parts(reverse=True)[1]

