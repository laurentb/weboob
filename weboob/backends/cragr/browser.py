# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.backends.cragr import pages

# Browser
class Cragr(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']

    is_logging = False

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.PAGES = {'https://%s/'              % website:   pages.LoginPage,
                      'https://%s/.*\.c.*'       % website:   pages.AccountsList,
                      'https://%s/login/process' % website:   pages.AccountsList,
                      'https://%s/accounting/listOperations' % website: pages.AccountsList,
                     }
        BaseBrowser.__init__(self, *args, **kwargs)

    def viewing_html(self):
        """
        As the fucking HTTP server returns a document in unknown mimetype
        'application/vnd.wap.xhtml+xml' it is not recognized by mechanize.

        So this is a fucking hack.
        """
        return True

    def home(self):
        self.location('https://%s/' % self.DOMAIN)

    def is_logged(self):
        return self.page and self.page.is_logged() or self.is_logging

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.is_logging = True
        if not self.is_on_page(pages.LoginPage):
            self.home()

        self.page.login(self.username, self.password)
        self.is_logging = False

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList) or self.page.is_account_page():
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    def get_history(self, account):
        page_url = account.link_id
        operations_count = 0
        while (page_url):
            self.location('https://%s%s' % (self.DOMAIN, page_url))
            for page_operation in self.page.get_history(operations_count):
                operations_count += 1
                yield page_operation
            page_url = self.page.next_page_url()

    #def get_coming_operations(self, account):
    #    if not self.is_on_page(pages.AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()
