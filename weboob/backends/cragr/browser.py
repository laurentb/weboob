# -*- coding: utf-8 -*-

"""
Copyright(C) 2009-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.tools.browser import Browser, BrowserIncorrectPassword
from weboob.backends.cragr import pages

# Browser
class Cragr(Browser):
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = 'Wget/1.11.4'

    is_logging = False

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.PAGES = {'https://%s/'           % website:   pages.LoginPage,
                      'https://%s/.*\.c.*'    % website:   pages.AccountList,
                     }
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://m.lefil.com/')

    def is_logged(self):
        return not self.is_on_page(pages.LoginPage) or self.is_logging

    def login(self):
        assert isinstance(self.username, (str,unicode))
        assert isinstance(self.password, (str,unicode))

        if not self.is_on_page(pages.LoginPage):
            self.home()

        self.is_logging = True
        self.page.login(self.username, self.password)

        if self.is_on_page(pages.LoginPage):
            raise BrowserIncorrectPassword()
        self.is_logging = False

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList):
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, (int, long))

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    #def get_coming_operations(self, account):
    #    if not self.is_on_page(pages.AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()
