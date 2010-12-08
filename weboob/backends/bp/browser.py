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


from datetime import datetime

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BrowserBanned

from .pages import LoginPage, LoggedPage, CookiePage, AccountList, AccountHistory, BadLoginPage, AccountDesactivate, \
                   TransferChooseAccounts, CompleteTransfer, TransferConfirm, TransferSummary

from weboob.capabilities.bank import Transfer


__all__ = ['BPBrowser']


class BPBrowser(BaseBrowser):
    DOMAIN = 'voscomptesenligne.labanquepostale.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {r'.*wsost/OstBrokerWeb/loginform.*':                               LoginPage,
             r'.*voscomptes/canalXHTML/identif\.ea.*':                          LoggedPage,
             r'.*voscomptes/canalXHTML/releve/syntheseAssurancesEtComptes\.ea': CookiePage,
             r'.*voscomptes/canalXHTML/releve/liste_comptes\.jsp':              AccountList,
             r'.*canalXHTML/relevesCCP/.*':                                     AccountHistory,
             r'.*canalXHTML/relevesEpargnes/.*':                                AccountHistory,
             r'.*ost/messages\.CVS\.html\?param=0x132120c8.*' :                 BadLoginPage,
             r'.*ost/messages\.CVS\.html\?param=0x132120cb.*' :                 AccountDesactivate,

             r'.*/virementsafran/aiguillage/saisieComptes\.ea.*':               TransferChooseAccounts,
             r'.*/virementsafran/aiguillage/2-saisieComptes\.ea.*' :            CompleteTransfer,
             r'.*/virementsafran/virementnational/2-virementNational\.ea.*' :   TransferConfirm,
             r'.*/virementsafran/virementnational/4-virementNational\.ea.*' :   TransferSummary,
             }

    def home(self):
        self.location('https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&'
            'ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location('https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&'
                'ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers',
                no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(BadLoginPage):
            raise BrowserIncorrectPassword()
        if self.is_on_page(AccountDesactivate):
            raise BrowserBanned()

    def get_accounts_list(self):
        self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/authentification/'
            'liste_contrat_atos.ea')
        self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/releve/liste_comptes.jsp')
        return self.page.get_accounts_list()

    def get_account(self, id):
        if not self.is_on_page(AccountList):
            self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/authentification/'
                'liste_contrat_atos.ea')
            self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/releve/liste_comptes.jsp')
        return self.page.get_account(id)

    def get_history(self, Account):
        self.location(Account.link_id)
        return self.page.get_history()

    def make_transfer(self, from_account, to_account, amount):
        self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virementsafran/aiguillage/'
            'saisieComptes.ea')
        self.page.set_accouts(from_account, to_account)

        #TODO: Check
        self.page.complete_transfer(amount)

        self.page.confirm()

        id_transfer = self.page.get_transfer_id()
        transfer = Transfer(id_transfer)
        transfer.amount = amount
        transfer.origin = from_account.label
        transfer.recipient = to_account.label
        transfer.date = datetime.now()
        return transfer
