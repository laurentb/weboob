<%inherit file="layout.py"/>
from weboob.tools.browser import BasePage


__all__ = ['Page1', 'Page2']


class Page1(BasePage):
    def do_stuff(self, _id):
        raise NotImplementedError()


class Page2(BasePage):
    def do_more_stuff(self):
        raise NotImplementedError()
