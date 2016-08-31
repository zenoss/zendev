import json
import py
import sys

from .log import info, error

CONFIG_DIR = "~/.zendev"


class ZendevConfig(object):
    def __init__(self, path):
        self._path = py.path.local(path)
        if self._path.check():
            with self._path.open() as f:
                try:
                    self._data = json.load(f)
                except ValueError as e:
                    print "File %s has invalid JSON data: %s" % (f,e)
                    self._data = {
                       'environments':{}
                    }
        else:
            self._data = {
                'environments':{}
            }

    def save(self):
        self._path.write(json.dumps(self._data, indent=4))

    @property
    def environments(self):
        return self._data.setdefault('environments', {})

    @property
    def current(self):
        return self._data.get('current')

    @current.setter
    def current(self, val):
        self._data['current'] = val
        self.save()

    def exists(self, name):
        return name in self.environments

    def add(self, name, path):
        path = py.path.local(path)
        if not self.exists(name):
            self.environments[name] = {'path': path.strpath}
            self.save()

    def remove(self, name, keepdata=True):
        env = self.environments.pop(name, None)
        if env:
            path = env.get('path')
            if keepdata:
                info("Environment {name} removed. Data still lives at {path}.".format(**locals()))
            else:
                try:
                    py.path.local(env.get('path')).remove()
                    info("Environment {name} and all data at {path} removed.".format(**locals()))
                except Exception:
                    error("Environment {name} removed, but unable to remove data at {path}.".format(**locals()))
            self.save()

    def validate(self, envName):
        if not envName:
            return True

        if not self.exists(envName):
            error("Environment '%s' is not defined" % envName)
            return False

        env = self.environments[envName]
        if not 'version' in env or env['version'] != "zendev2":
            error("Environment '%s' is not compatible with zendev2" % envName)
            return False

        return True


def get_config():
    zendevhome = py.path.local(CONFIG_DIR, expanduser=True).ensure(dir=True)
    config = ZendevConfig(zendevhome.join('environments.json'))

    config.save()
    return config


def get_envname():
    return get_config().current
