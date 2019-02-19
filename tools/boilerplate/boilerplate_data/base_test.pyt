<%inherit file="layout.pyt"/>
from weboob.tools.test import BackendTest


class ${r.classname}Test(BackendTest):
    MODULE = '${r.name}'
