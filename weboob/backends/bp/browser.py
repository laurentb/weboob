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

from .pages import LoginPage, Initident, CheckPassword, repositionnerCheminCourant, BadLoginPage, AccountDesactivate, \
                   AccountList, AccountHistory, \
                   TransferChooseAccounts, CompleteTransfer, TransferConfirm, TransferSummary

from weboob.capabilities.bank import Transfer


__all__ = ['BPBrowser']


class BPBrowser(BaseBrowser):
    DOMAIN = 'voscomptesenligne.labanquepostale.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {r'.*wsost/OstBrokerWeb/loginform.*'                                         : LoginPage,
             r'.*authentification/repositionnerCheminCourant-identif.ea'                 : repositionnerCheminCourant,
             r'.*authentification/initialiser-identif.ea'                                : Initident,
             r'.*authentification/verifierMotDePasse-identif.ea'                         : CheckPassword,
             
             r'.*synthese_assurancesEtComptes/afficheSynthese-synthese\.ea'              : AccountList,
             r'.*synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea'     : AccountList,
             
             r'.*CCP/releves_ccp/releveCPP-releve_ccp\.ea'                               : AccountHistory,
             r'.*CNE/releveCNE/releveCNE-releve_cne\.ea'                                 : AccountHistory,
             
             r'.*/virementSafran_aiguillage/init-saisieComptes\.ea'                      : TransferChooseAccounts,
             r'.*/virementSafran_aiguillage/formAiguillage-saisieComptes\.ea'            : CompleteTransfer,
             r'.*/virementSafran_national/validerVirementNational-virementNational.ea'   : TransferConfirm,
             r'.*/virementSafran_national/confirmerVirementNational-virementNational.ea' : TransferSummary,

             r'.*ost/messages\.CVS\.html\?param=0x132120c8.*'                            : BadLoginPage,
             r'.*ost/messages\.CVS\.html\?param=0x132120cb.*'                            : AccountDesactivate,
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
        self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea")
        return self.page.get_accounts_list()

    def get_account(self, id):
        if not self.is_on_page(AccountList):
            self.location("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea")
        return self.page.get_account(id)

    def get_history(self, Account):
        self.location(Account.link_id)
        return self.page.get_history()

    def make_transfer(self, from_account, to_account, amount):
        self.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/virement/virementSafran_aiguillage/init-saisieComptes.ea')
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
