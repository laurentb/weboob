<%inherit file="layout.py"/>
from weboob.tools.browser2 import PagesBrowser, URL

from .pages import Page1, Page2


__all__ = ['${r.classname}Browser']


class ${r.classname}Browser(PagesBrowser):
    BASEURL = 'http://www.${r.name}.com'

    page1 = URL('/page1\?id=(?P<id>.+)', Page1)
    page2 = URL('/page2', Page2)

    def get_stuff(self, _id):
        self.page1.go(id=_id)

        assert self.page1.is_here()
        self.page.do_stuff(_id)

        assert self.page2.is_here()
        return self.page.do_more_stuff()
