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


from urllib import urlencode
from urlparse import urlsplit, parse_qsl
from datetime import datetime

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserBanned

from .pages import LoginPage, Initident, CheckPassword, repositionnerCheminCourant, BadLoginPage, AccountDesactivate, \
                   AccountList, AccountHistory, CardsList, UnavailablePage, AccountRIB, \
                   TransferChooseAccounts, CompleteTransfer, TransferConfirm, TransferSummary
from .pages.pro import RedirectPage, ProAccountsList, ProAccountHistory, ProAccountHistoryDownload, ProAccountHistoryCSV, DownloadRib, RibPage

from weboob.capabilities.bank import Transfer


__all__ = ['BPBrowser', 'BProBrowser']


class BPBrowser(LoginBrowser):
    BASEURL = 'https://voscomptesenligne.labanquepostale.fr'
    CERTHASH = ['184ccdf506ce87e66cba71ce754e48aa51720f346df56ed27399006c288a82ce', '5719e6295761eb6de357d5e0743a26b917c4346792aff657f585c83cd7eae8f7']

    login_page = URL(r'.*wsost/OstBrokerWeb/loginform.*', LoginPage)
    repositionner_chemin_courant = URL(r'.*authentification/repositionnerCheminCourant-identif.ea', repositionnerCheminCourant)
    init_ident = URL(r'.*authentification/initialiser-identif.ea', Initident)
    check_password = URL(r'.*authentification/verifierMotDePasse-identif.ea', CheckPassword)

    redirect_page = URL(r'.*voscomptes/identification/identification.ea.*',
                        r'.*voscomptes/synthese/3-synthese.ea',
                        RedirectPage)

    accounts_list = URL(r'.*synthese_assurancesEtComptes/afficheSynthese-synthese\.ea',
                        r'.*synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea',
                        r'/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/preparerRechercheListePrets-synthese.ea',
                        AccountList)
    accounts_rib = URL(r'.*voscomptes/canalXHTML/comptesCommun/imprimerRIB/init-imprimer_rib.ea.*', AccountRIB)

    pro_accounts_list = URL(r'.*voscomptes/synthese/synthese.ea', ProAccountsList)
    pro_history = URL(r'.*voscomptes/historiqueccp/historiqueccp.ea.*', ProAccountHistory)
    pro_history_dl = URL(r'.*voscomptes/telechargercomptes/telechargercomptes.ea.*', ProAccountHistoryDownload)
    pro_history_csv = URL(r'.*voscomptes/telechargercomptes/1-telechargercomptes.ea', ProAccountHistoryCSV) # HistoryParser()?

    account_history = URL(r'.*CCP/releves_ccp/releveCPP-releve_ccp\.ea',
                          r'.*CNE/releveCNE/releveCNE-releve_cne\.ea',
                          r'.*CB/releveCB/preparerRecherche-mouvementsCarteDD.ea.*',
                          AccountHistory)
    cards_list = URL(r'.*CB/releveCB/init-mouvementsCarteDD.ea.*', CardsList)

    transfer_choose = URL(r'.*/virementSafran_aiguillage/init-saisieComptes\.ea', TransferChooseAccounts)
    transfer_complete = URL(r'.*/virementSafran_aiguillage/formAiguillage-saisieComptes\.ea', CompleteTransfer)
    transfer_confirm = URL(r'.*/virementSafran_national/validerVirementNational-virementNational.ea', TransferConfirm)
    transfer_summary = URL(r'.*/virementSafran_national/confirmerVirementNational-virementNational.ea', TransferSummary)

    badlogin = URL(r'.*ost/messages\.CVS\.html\?param=0x132120c8.*', BadLoginPage)
    disabled_account = URL(r'.*ost/messages\.CVS\.html\?param=0x132120cb.*',
                           r'.*/message\.html\?param=0x132120c.*',
                           AccountDesactivate)
    unavailable = URL(r'https?://.*.labanquepostale.fr/delestage.html', UnavailablePage)
    rib_dl = URL(r'.*/voscomptes/rib/init-rib.ea', DownloadRib)
    rib = URL(r'.*/voscomptes/rib/preparerRIB-rib.*', RibPage)

    login_url = 'https://voscomptesenligne.labanquepostale.fr/wsost/OstBrokerWeb/loginform?TAM_OP=login&' \
            'ERROR_CODE=0x00000000&URL=%2Fvoscomptes%2FcanalXHTML%2Fidentif.ea%3Forigin%3Dparticuliers'
    accounts_url = "https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/rechercheContratAssurance-synthese.ea"
    accounts_and_loans_url = "https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/preparerRechercheListePrets-synthese.ea"

    #def home(self):
    #    self.do_login()

    def do_login(self):
        self.location(self.login_url)

        self.page.login(self.username, self.password)

        if self.redirect_page.is_here() and self.page.check_for_perso():
            raise BrowserIncorrectPassword(u"L'identifiant utilisé est celui d'un compte de Particuliers.")
        if self.badlogin.is_here():
            raise BrowserIncorrectPassword()
        if self.disabled_account.is_here():
            raise BrowserBanned()

    @need_login
    def get_accounts_list(self):
        ids = set()

        self.location(self.accounts_url)
        assert self.accounts_list.is_here()
        for account in self.page.get_accounts_list():
            ids.add(account.id)
            yield account

        if self.accounts_and_loans_url:
            self.location(self.accounts_and_loans_url)
            assert self.accounts_list.is_here()

            for account in self.page.get_accounts_list():
                if account.id not in ids:
                    ids.add(account.id)
                    yield account

    @need_login
    def get_account(self, id):
        if not self.accounts_list.is_here():
            self.location(self.accounts_url)
        return self.page.get_account(id)

    @need_login
    def get_history(self, account):
        v = urlsplit(account._link_id)
        args = dict(parse_qsl(v.query))
        args['typeRecherche'] = 10

        self.location('%s?%s' % (v.path, urlencode(args)))

        transactions = []

        if self.account_history.is_here():
            for tr in self.page.get_history():
                transactions.append(tr)

        for tr in self.get_coming(account):
            transactions.append(tr)

        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        return transactions

    @need_login
    def get_coming(self, account):
        transactions = []

        for card in account._card_links:
            self.location(card)


            if self.cards_list.is_here():
                for link in self.page.get_cards():
                    self.location(link)

                    for tr in self._iter_card_tr():
                        transactions.append(tr)
            else:
                for tr in self._iter_card_tr():
                    transactions.append(tr)

        transactions.sort(key=lambda tr: tr.rdate, reverse=True)
        return transactions

    @need_login
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

    @need_login
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
    accounts_and_loans_url = None

    def do_login(self):
        super(BProBrowser, self).do_login()

        v = urlsplit(self.page.url)
        version = v.path.split('/')[1]

        self.base_url = 'https://banqueenligne.entreprises.labanquepostale.fr/%s' % version
        self.accounts_url = self.base_url + '/voscomptes/synthese/synthese.ea'

    @need_login
    def get_accounts_list(self):
        accounts = BPBrowser.get_accounts_list(self)
        for acc in accounts:
            self.location('%s/voscomptes/rib/init-rib.ea' % self.base_url)
            value = self.page.get_rib_value(acc.id)
            if value:
                self.location('%s/voscomptes/rib/preparerRIB-rib.ea?%s' % (self.base_url, value))
                if self.rib.is_here():
                    acc.iban = self.page.get_iban()
            yield acc
