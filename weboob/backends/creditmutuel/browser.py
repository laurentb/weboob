# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
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

from .pages import LoginPage, LoginErrorPage, AccountsPage, OperationsPage


__all__ = ['CreditMutuelBrowser']


# Browser
class CreditMutuelBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'www.creditmutuel.fr'
    ENCODING = 'iso-8859-1'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {'https://www.creditmutuel.fr/groupe/fr/index.html':   LoginPage,
             'https://www.creditmutuel.fr/groupe/fr/identification/default.cgi': LoginErrorPage,
         'https://www.creditmutuel.fr/cmdv/fr/banque/situation_financiere.cgi': AccountsPage,
         'https://www.creditmutuel.fr/cmdv/fr/banque/mouvements.cgi.*' : OperationsPage
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page and not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://www.creditmutuel.fr/', no_login=True)

        self.page.login( self.username, self.password)

        if not self.is_logged() or self.is_on_page(LoginErrorPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        page_url = account.link_id
        #operations_count = 0
        while (page_url):
            self.location('https://%s/cmdv/fr/banque/%s' % (self.DOMAIN, page_url))
            #for page_operation in self.page.get_history(operations_count):
            #    operations_count += 1
            #    yield page_operation
            for op in self.page.get_history():
                yield op
            page_url = self.page.next_page_url()


    #def get_coming_operations(self, account):
    #    if not self.is_on_page(AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()
