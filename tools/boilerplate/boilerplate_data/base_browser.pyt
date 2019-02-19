<%inherit file="layout.pyt"/>
from weboob.browser import ${'LoginBrowser, need_login' if r.login else 'PagesBrowser'}, URL

from .pages import Page1, Page2


class ${r.classname}Browser(${'Login' if r.login else 'Pages'}Browser):
    BASEURL = 'http://www.${r.name}.com'

    page1 = URL('/page1\?id=(?P<id>.+)', Page1)
    page2 = URL('/page2', Page2)

% if login:
    def do_login(self):
        pass

    @need_login
% endif
    def get_stuff(self, _id):
        self.page1.go(id=_id)

        assert self.page1.is_here()
        self.page.do_stuff(_id)

        assert self.page2.is_here()
        return self.page.do_more_stuff()
