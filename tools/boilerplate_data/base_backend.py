<%inherit file="layout.py"/>
from weboob.tools.backend import BaseBackend

from .browser import ${r.classname}Browser


__all__ = ['${r.classname}Backend']


class ${r.classname}Backend(BaseBackend):
    NAME = '${r.name}'
    DESCRIPTION = '${r.name} website'
    MAINTAINER = '${r.author}'
    EMAIL = '${r.email}'
    VERSION = '${r.version}'

    DOMAIN = 'www.${r.name}.com'
    BROWSER = ${r.classname}Browser
