<%inherit file="layout.py"/>
from weboob.tools.browser import BaseBrowser

from .pages import Page1, Page2


__all__ = ['${r.classname}Browser']


class ${r.classname}Browser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.${r.name}.com'
    ENCODING = None

    PAGES = {
        '%s://%s/page1\?id=.+' % (PROTOCOL, DOMAIN): Page1,
        '%s://%s/page2' % (PROTOCOL, DOMAIN): Page2,
    }

    def get_stuff(self, _id):
        self.location('%s://%s/page1?id=%s' % (self.PROTOCOL, self.DOMAIN, _id))
        assert self.is_on_page(Page1)
        self.page.do_stuff(_id)
        assert self.is_on_page(Page2)
        return self.page.do_more_stuff()
