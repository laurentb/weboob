<%inherit file="layout.py"/>
from weboob.tools.test import BackendTest


class ${r.classname}Test(BackendTest):
    BACKEND = '${r.name}'

    def test_${r.name}(self):
        raise NotImplementedError()
