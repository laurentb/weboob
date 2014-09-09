<%inherit file="layout.py"/>
from weboob.tools.browser2 import HTMLPage


class Page1(HTMLPage):
    def do_stuff(self, _id):
        raise NotImplementedError()


class Page2(HTMLPage):
    def do_more_stuff(self):
        raise NotImplementedError()
