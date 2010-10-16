# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from urlparse import urlsplit

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages.index import LoginPage, IndexPage, MyPage
from .pages.wiki import WikiPage, WikiEditPage


__all__ = ['RedmineBrowser']


# Browser
class RedmineBrowser(BaseBrowser):
    ENCODING = 'utf-8'
    PAGES = {'%s/':                              IndexPage,
             '%s/login':                         LoginPage,
             '%s/my/page':                       MyPage,
             '%s/projects/\w+/wiki/\w+/edit':    WikiEditPage,
             '%s/projects/\w+/wiki/\w*':         WikiPage,
            }

    is_logging = False

    def __init__(self, url, *args, **kwargs):
        v = urlsplit(url)
        self.PROTOCOL = v.scheme
        self.DOMAIN = v.netloc
        self.BASEPATH = v.path
        if self.BASEPATH.endswith('/'):
            self.BASEPATH = self.BASEPATH[:-1]

        prefix = '%s://%s%s' % (self.PROTOCOL, self.DOMAIN, self.BASEPATH)

        self.PAGES = {}
        for key, value in RedmineBrowser.PAGES.iteritems():
            self.PAGES[key % prefix] = value
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.is_logging or (self.page and len(self.page.document.getroot().cssselect('a.my-account')) == 1)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.is_logging = True
        if not self.is_on_page(LoginPage):
            self.location('%s/login' % self.BASEPATH)

        self.page.login(self.username, self.password)

        self.is_logging = False
        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_wiki_source(self, project, page):
        self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, page))
        return self.page.get_source()

    def set_wiki_source(self, project, page, data, message):
        self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, page))
        self.page.set_source(data, message)
