<%inherit file="layout.pyt"/>
from weboob.browser.pages import HTMLPage


class Page1(HTMLPage):
    def do_stuff(self, _id):
        raise NotImplementedError()


class Page2(HTMLPage):
    def do_more_stuff(self):
        raise NotImplementedError()
