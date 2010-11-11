# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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


from weboob.tools.browser import BaseBrowser#, BrowserIncorrectPassword

from .pages import LoginPage, LoggedPage, CookiePage, AccountList, AccountHistory


__all__ = ['BPbrowser']


class BPbrowser(BaseBrowser):
    DOMAIN = 'voscomptesenligne.labanquepostale.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = { r'.*wsost/OstBrokerWeb/loginform.*':                              LoginPage,
              r'.*voscomptes/canalXHTML/identif.ea':                            LoggedPage,
              r'.*voscomptes/canalXHTML/releve/syntheseAssurancesEtComptes.ea': CookiePage,
              r'.*voscomptes/canalXHTML/releve/liste_comptes.jsp':              AccountList,
              r'.*canalXHTML/relevesCCP/.*':                                    AccountHistory,
              r'.*canalXHTML/relevesEpargnes/.*':                               AccountHistory,


            }

    def home(self):
        self.location("https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers")

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location('https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers', no_login=True)

        self.page.login(self.username, self.password)

    def get_accounts_list(self):
        self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/authentification/liste_contrat_atos.ea")
        self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/releve/liste_comptes.jsp")
        return self.page.get_accounts_list()

    def get_account(self, id):

        if not self.is_on_page(AccountList):
            self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/authentification/liste_contrat_atos.ea")
            self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/releve/liste_comptes.jsp")
        return self.page.get_account(id)


    def get_history(self, Account):
        self.location(Account.link_id)
        return self.page.get_history()
