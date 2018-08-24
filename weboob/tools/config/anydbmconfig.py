# -*- coding: utf-8 -*-

import yaml

from .iconfig import ConfigError, IConfig
from .yamlconfig import WeboobDumper

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

try:
    import anydbm as dbm
except ImportError:
    import dbm


__all__ = ['AnyDBMConfig']


class AnyDBMConfig(IConfig):
    def __init__(self, path):
        self.path = path

    def load(self, default={}):
        self.storage = dbm.open(self.path, 'c')

    def save(self):
        pass

    def get(self, *args, **kwargs):
        key = '.'.join(args)
        try:
            value = self.storage[key]
            value = yaml.load(value, Loader=Loader)
        except KeyError:
            if 'default' in kwargs:
                value = kwargs.get('default')
            else:
                raise ConfigError()
        except TypeError:
            raise ConfigError()
        return value

    def set(self, *args):
        key = '.'.join(args[:-1])
        value = args[-1]
        try:
            self.storage[key] = yaml.dump(value, None, Dumper=WeboobDumper, default_flow_style=False)
        except KeyError:
            raise ConfigError()
        except TypeError:
            raise ConfigError()

    def delete(self, *args):
        key = '.'.join(args)
        try:
            del self.storage[key]
        except KeyError:
            raise ConfigError()
        except TypeError:
            raise ConfigError()
