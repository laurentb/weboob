# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


from urlparse import urlsplit, parse_qsl
from datetime import datetime

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserBanned
from weboob.deprecated.browser.parsers.iparser import RawParser

from .pages import LoginPage, Initident, CheckPassword, repositionnerCheminCourant, BadLoginPage, AccountDesactivate, \
                   AccountList, AccountHistory, CardsList, UnavailablePage, AccountRIB, \
                   TransferChooseAccounts, CompleteTransfer, TransferConfirm, TransferSummary
from .pages.pro import RedirectPage, ProAccountsList, ProAccountHistory, ProAccountHistoryDownload, ProAccountHistoryCSV, HistoryParser, DownloadRib, RibPage

from weboob.capabilities.bank import Transfer


__all__ = ['BPBrowser', 'BProBrowser']


class BPBrowser(Browser):
    DOMAIN = 'voscomptesenligne.labanquepostale.fr'
    PROTOCOL = 'https'
    CERTHASH = ['184ccdf506ce87e66cba71ce754e48aa51720f346df56ed27399006c288a82ce', '5719e6295761eb6de357d5e0743a26b917c4346792aff657f585c83cd7eae8f7']
    ENCODING = 'iso-8859-1'
    PAGES = {r'.*wsost/OstBrokerWeb/loginform.*'                                         : LoginPage,
             r'.*authentification/repositionnerCheminCourant-identif.ea'                 : repositionnerCheminCourant,
             r'.*authentification/initialiser-identif.ea'                                : Initident,
             r'.*authentification/verifierMotDePasse-identif.ea'                         : CheckPassword,

             r'.*voscomptes/identification/identification.ea.*'                          : RedirectPage,

             r'.*synthese_assurancesEtComptes/afficheSynthese-synthese\.ea'              : AccountList,
             r'.*synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea'     : AccountList,
             r'.*voscomptes/canalXHTML/comptesCommun/imprimerRIB/init-imprimer_rib.ea.*' : (AccountRIB, RawParser()),

             r'.*voscomptes/synthese/3-synthese.ea'                                      : RedirectPage,
             r'.*voscomptes/synthese/synthese.ea'                                        : ProAccountsList,
             r'.*voscomptes/historiqueccp/historiqueccp.ea.*'                            : ProAccountHistory,
             r'.*voscomptes/telechargercomptes/telechargercomptes.ea.*'                  : ProAccountHistoryDownload,
             r'.*voscomptes/telechargercomptes/1-telechargercomptes.ea'                  : (ProAccountHistoryCSV, HistoryParser()),

             r'.*CCP/releves_ccp/releveCPP-releve_ccp\.ea'                               : AccountHistory,
             r'.*CNE/releveCNE/releveCNE-releve_cne\.ea'                                 : AccountHistory,
             r'.*CB/releveCB/preparerRecherche-mouvementsCarteDD.ea.*'                   : AccountHistory,
             r'.*CB/releveCB/init-mouvementsCarteDD.ea.*'                                : CardsList,

             r'.*/virementSafran_aiguillage/init-saisieComptes\.ea'                      : TransferChooseAccounts,
             r'.*/virementSafran_aiguillage/formAiguillage-saisieComptes\.ea'            : CompleteTransfer,
             r'.*/virementSafran_national/validerVirementNational-virementNational.ea'   : TransferConfirm,
             r'.*/virementSafran_national/confirmerVirementNational-virementNational.ea' : TransferSummary,

             r'.*ost/messages\.CVS\.html\?param=0x132120c8.*'                            : BadLoginPage,
             r'.*ost/messages\.CVS\.html\?param=0x132120cb.*'                            : AccountDesactivate,
             r'https?://.*.labanquepostale.fr/delestage.html'                            : UnavailablePage,
             r'.*/voscomptes/rib/init-rib.ea'                                            : DownloadRib,
             r'.*/voscomptes/rib/preparerRIB-rib.*'                                      : RibPage,
             }

    login_url = 'https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&' \
            'ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers'
    accounts_url = "https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea"

    def __init__(self, *args, **kwargs):
        kwargs['parser'] = ('lxml',)
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.login()

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.location(self.login_url, no_login=True)

        self.page.login(self.username, self.password)

        if self.is_on_page(RedirectPage) and self.page.check_for_perso():
            raise BrowserIncorrectPassword()
        if self.is_on_page(BadLoginPage):
            raise BrowserIncorrectPassword()
        if self.is_on_page(AccountDesactivate):
            raise BrowserBanned()

    def get_accounts_list(self):
        self.location(self.accounts_url)
        return self.page.get_accounts_list()

    def get_account(self, id):
        if not self.is_on_page(AccountList):
            self.location(self.accounts_url)
        return self.page.get_account(id)

    def get_history(self, account):
        v = urlsplit(account._link_id)
        args = dict(parse_qsl(v.query))
        args['typeRecherche'] = 10

        self.location(self.buildurl(v.path, **args))

        if self.is_on_page(AccountHistory):
            for tr in self.page.get_history():
                yield tr

        for tr in self.get_coming(account):
            yield tr

    def get_coming(self, account):
        for card in account._card_links:
            self.location(card)

            if self.is_on_page(CardsList):
                for link in self.page.get_cards():
                    self.location(link)

                    for tr in self._iter_card_tr():
                        yield tr
            else:
                for tr in self._iter_card_tr():
                    yield tr

    def _iter_card_tr(self):
        """
        Iter all pages until there are no transactions.
        """
        ops = self.page.get_history(deferred=True)

        while True:
            for tr in ops:
                yield tr

            link = self.page.get_next_link()
            if link is None:
                return

            self.location(link)
            ops = self.page.get_history(deferred=True)

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

class BProBrowser(BPBrowser):
    login_url = "https://banqueenligne.entreprises.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&ERROR_CODE=0x00000000&URL=%2Fws_q47%2Fvoscomptes%2Fidentification%2Fidentification.ea%3Forigin%3Dprofessionnels"

    def login(self):
        BPBrowser.login(self)

        v = urlsplit(self.page.url)
        version = v.path.split('/')[1]

        self.base_url = 'https://banqueenligne.entreprises.labanquepostale.fr/%s' % version
        self.accounts_url = self.base_url + '/voscomptes/synthese/synthese.ea'

    def get_accounts_list(self):
        accounts = BPBrowser.get_accounts_list(self)
        for acc in accounts:
            self.location('%s/voscomptes/rib/init-rib.ea' % self.base_url)
            value = self.page.get_rib_value(acc.id)
            if value:
                self.location('%s/voscomptes/rib/preparerRIB-rib.ea?%s' % (self.base_url, value))
                if self.is_on_page(RibPage):
                    acc.iban = self.page.get_iban()
            yield acc


