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

from .pages import LoginPage, LoginErrorPage, AccountsPage, OperationsPage, InfoPage


__all__ = ['CreditMutuelBrowser']


# Browser
class CreditMutuelBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'www.creditmutuel.fr'
    ENCODING = 'iso-8859-1'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {'https://www.creditmutuel.fr/groupe/fr/index.html':   LoginPage,
             'https://www.creditmutuel.fr/groupe/fr/identification/default.cgi': LoginErrorPage,
         'https://www.creditmutuel.fr/.*/fr/banque/situation_financiere.cgi': AccountsPage,
         'https://www.creditmutuel.fr/.*/fr/banque/mouvements.cgi.*' : OperationsPage,
         'https://www.creditmutuel.fr/.*/fr/banque/BAD.*' : InfoPage
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)
        self.SUB_BANKS = ['cmdv','cmcee','cmse', 'cmidf', 'cmsmb', 'cmma', 'cmc', 'cmlaco', 'cmnormandie', 'cmm']

    def is_logged(self):
        return self.page and not self.is_on_page(LoginPage)

    def home(self):
        return self.location('https://www.creditmutuel.fr/groupe/fr/index.html')


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
            self.location('https://www.creditmutuel.fr/%s/fr/banque/situation_financiere.cgi'%self.getCurrentSubBank())
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def getCurrentSubBank(self):
        # the account list and history urls depend on the sub bank of the user
        current_url = self.geturl()
        current_url_parts = current_url.split('/')
        for subbank in self.SUB_BANKS:
            print "\nploup %s\n"%subbank
            if subbank in current_url_parts:
                return subbank

    def get_history(self, account):
        page_url = account.link_id
        #operations_count = 0
        l_ret = []
        while (page_url):
            self.location('https://%s/%s/fr/banque/%s' % (self.DOMAIN, self.getCurrentSubBank(), page_url))
            #for page_operation in self.page.get_history(operations_count):
            #    operations_count += 1
            #    yield page_operation
            
            ## FONCTIONNE
            #for op in self.page.get_history():
            #    yield op

            ## FONTIONNE
            #return self.page.get_history()
            
            for op in self.page.get_history():
                l_ret.append(op)
            page_url = self.page.next_page_url()

        return l_ret


    #def get_coming_operations(self, account):
    #    if not self.is_on_page(AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()
