# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from urlparse import urlsplit
import urllib
import lxml.html

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
             '%s/projects/([\w-]+)/wiki/([\w_\-]+)/edit':    WikiEditPage,
             '%s/projects/[\w-]+/wiki/[\w_\-]*':         WikiPage,
            }

    def __init__(self, url, *args, **kwargs):
        self._userid = 0
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
        return self.is_on_page(LoginPage) or self.page and len(self.page.document.getroot().cssselect('a.my-account')) == 1

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('%s/login' % self.BASEPATH, no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

        divs = self.page.document.getroot().cssselect('div#loggedas')
        if len(divs) > 0:
            parts = divs[0].find('a').attrib['href'].split('/')
            self._userid = int(parts[2])

    def get_userid(self):
        return self._userid

    def get_wiki_source(self, project, page):
        self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, page))
        return self.page.get_source()

    def set_wiki_source(self, project, page, data, message):
        self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH, project, page))
        self.page.set_source(data, message)

    def get_wiki_preview(self, project, page, data):
        if (not self.is_on_page(WikiEditPage) or self.page.groups[0] != project
            or self.page.groups[1] != page):
            self.location('%s/projects/%s/wiki/%s/edit' % (self.BASEPATH,
                                                           project, page))
        url = '%s/projects/%s/wiki/%s/preview' % (self.BASEPATH, project, page)
        params = {}
        params['content[text]'] = data.encode('utf-8')
        params['authenticity_token'] = "%s" % self.page.get_authenticity_token()
        preview_html = lxml.html.fragment_fromstring(self.readurl(url,
                                                    urllib.urlencode(params)),
                                                    create_parent='div')
        preview_html.find("fieldset").drop_tag()
        preview_html.find("legend").drop_tree()
        return lxml.html.tostring(preview_html)

