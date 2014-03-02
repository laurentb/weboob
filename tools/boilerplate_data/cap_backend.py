<%inherit file="layout.py"/>
from weboob.tools.backend import BaseBackend
from ${r.capmodulename} import ${r.capname}

from .browser import ${r.classname}Browser


__all__ = ['${r.classname}Backend']


class ${r.classname}Backend(BaseBackend, ${r.capname}):
    NAME = '${r.name}'
    DESCRIPTION = u'${r.name} website'
    MAINTAINER = u'${r.author}'
    EMAIL = '${r.email}'
    LICENSE = 'AGPLv3+'
    VERSION = '${r.version}'

    BROWSER = ${r.classname}Browser

${r.methods_code}
