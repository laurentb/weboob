# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

import json

from weboob.browser import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.base import find_object
from weboob.tools.capabilities.bank.transactions import sorted_transactions, FrenchTransaction

from .pages import (
    ErrorPage,
    LoginPage, CenetLoginPage, CenetHomePage,
    CenetAccountsPage, CenetAccountHistoryPage, CenetCardsPage,
    CenetCardSummaryPage,
)
from ..pages import CaissedepargneKeyboard


__all__ = ['CenetBrowser']


class CenetBrowser(LoginBrowser, StatesMixin):
    BASEURL = "https://www.cenet.caisse-epargne.fr"
    STATE_DURATION = 5

    login = URL(r'https://(?P<domain>[^/]+)/authentification/manage\?step=identification&identifiant=(?P<login>.*)',
                r'https://.*/authentification/manage\?step=identification&identifiant=.*',
                r'https://.*/login.aspx', LoginPage)
    account_login = URL('/authentification/manage\?step=account&identifiant=(?P<login>.*)&account=(?P<accountType>.*)', LoginPage)
    cenet_vk = URL('https://www.cenet.caisse-epargne.fr/Web/Api/ApiAuthentification.asmx/ChargerClavierVirtuel')
    cenet_home = URL('/Default.aspx$', CenetHomePage)
    cenet_accounts = URL('/Web/Api/ApiComptes.asmx/ChargerSyntheseComptes', CenetAccountsPage)
    cenet_account_history = URL('/Web/Api/ApiComptes.asmx/ChargerHistoriqueCompte', CenetAccountHistoryPage)
    cenet_account_coming = URL('/Web/Api/ApiCartesBanquaires.asmx/ChargerEnCoursCarte', CenetAccountHistoryPage)
    cenet_tr_detail = URL('/Web/Api/ApiComptes.asmx/ChargerDetailOperation', CenetCardSummaryPage)
    cenet_cards = URL('/Web/Api/ApiCartesBanquaires.asmx/ChargerCartes', CenetCardsPage)
    error = URL(r'https://.*/login.aspx',
                r'https://.*/Pages/logout.aspx.*',
                r'https://.*/particuliers/Page_erreur_technique.aspx.*', ErrorPage)
    cenet_login = URL(r'https://.*/$',
                      r'https://.*/default.aspx', CenetLoginPage)

    __states__ = ('BASEURL',)

    def __init__(self, nuser, *args, **kwargs):
        # The URL to log in and to navigate are different
        self.login_domain = kwargs.pop('domain', self.BASEURL)
        if not self.BASEURL.startswith('https://'):
            self.BASEURL = 'https://%s' % self.BASEURL

        self.accounts = None
        self.nuser = nuser

        super(CenetBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        data = self.login.go(login=self.username, domain=self.login_domain).get_response()

        if data is None:
            raise BrowserIncorrectPassword()

        assert "authMode" in data and data['authMode'] == 'redirect', 'should not be on the cenet website'

        payload = {'contexte': '', 'dataEntree': None, 'donneesEntree': "{}", 'filtreEntree': "\"false\""}
        res = self.cenet_vk.open(data=json.dumps(payload), headers={'Content-Type': "application/json"})
        content = json.loads(res.text)
        d = json.loads(content['d'])
        end = json.loads(d['DonneesSortie'])

        _id = end['Identifiant']
        vk = CaissedepargneKeyboard(end['Image'], end['NumerosEncodes'])
        code = vk.get_string_code(self.password)

        post_data = {
            'CodeEtablissement': data['codeCaisse'],
            'NumeroBad': self.username,
            'NumeroUtilisateur': self.nuser
        }

        self.location(data['url'], data=post_data, headers={'Referer': 'https://www.cenet.caisse-epargne.fr/'})

        return self.page.login(self.username, self.password, self.nuser, data['codeCaisse'], _id, code)

    @need_login
    def get_accounts_list(self):
        if self.accounts is None:
            headers = {
                'Content-Type': 'application/json; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01'
            }

            data = {
                'contexte': '',
                'dateEntree': None,
                'donneesEntree': 'null',
                'filtreEntree': None
            }

            try:
                self.accounts = [account for account in self.cenet_accounts.go(data=json.dumps(data), headers=headers).get_accounts()]
            except ClientError:
                # Unauthorized due to wrongpass
                raise BrowserIncorrectPassword()

            for account in self.accounts:
                try:
                    account._cards = [card for card in self.cenet_cards.go(data=json.dumps(data), headers=headers).get_cards() \
                                    if card['Compte']['Numero'] == account.id]
                except BrowserUnavailable:
                    # for some accounts, the site can throw us an error, during weeks
                    self.logger.warning('ignoring cards because site is unavailable...')
                    account._cards = []

        return iter(self.accounts)

    def get_loans_list(self):
        return []

    @need_login
    def get_history(self, account):
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }

        data = {
            'contexte': '',
            'dateEntree': None,
            'filtreEntree': None,
            'donneesEntree': json.dumps(account._formated),
        }

        items = []
        self.cenet_account_history.go(data=json.dumps(data), headers=headers)
        # there might be some duplicate transactions regarding the card type ones
        # because some requests lead to the same transaction list
        # even with different parameters/data in the request
        card_tr_list = []
        while True:
            data_out = self.page.doc['DonneesSortie']
            for tr in self.page.get_history():
                items.append(tr)

                if tr.type is FrenchTransaction.TYPE_CARD_SUMMARY:
                    if find_object(card_tr_list, label=tr.label, amount=tr.amount, raw=tr.raw, date=tr.date, rdate=tr.rdate):
                        self.logger.warning('Duplicate transaction: %s' % tr)
                        continue
                    card_tr_list.append(tr)
                    tr.deleted = True
                    tr_dict = [tr_dict for tr_dict in data_out if tr_dict['Libelle'] == tr.label]
                    donneesEntree = {}
                    donneesEntree['Compte'] = account._formated
                    donneesEntree['ListeOperations'] = [tr_dict[0]]
                    deferred_data = {
                        'contexte': '',
                        'dateEntree': None,
                        'donneesEntree': json.dumps(donneesEntree).replace('/', '\\/'),
                        'filtreEntree': json.dumps(tr_dict[0]).replace('/', '\\/')
                    }
                    tr_detail_page = self.cenet_tr_detail.open(data=json.dumps(deferred_data), headers=headers)
                    for tr in tr_detail_page.get_history():
                        items.append(tr)

            offset = self.page.next_offset()
            if not offset:
                break

            data['filtreEntree'] = json.dumps({
                'Offset': offset,
            })
            self.cenet_account_history.go(data=json.dumps(data), headers=headers)

        return sorted_transactions(items)

    @need_login
    def get_coming(self, account):
        trs = []

        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }

        for card in account._cards:
            data = {
                'contexte': '',
                'dateEntree': None,
                'donneesEntree': json.dumps(card),
                'filtreEntree': None
            }

            for tr in self.cenet_account_coming.go(data=json.dumps(data), headers=headers).get_history():
                trs.append(tr)

        return sorted_transactions(trs)

    @need_login
    def get_investment(self, account):
        # not available for the moment
        return []

    @need_login
    def get_advisor(self):
        return [self.cenet_home.stay_or_go().get_advisor()]

    @need_login
    def get_profile(self):
        return self.cenet_home.stay_or_go().get_profile()

    def iter_recipients(self, origin_account):
        raise NotImplementedError()

    def init_transfer(self, account, recipient, transfer):
        raise NotImplementedError()

    def new_recipient(self, recipient, **params):
        raise NotImplementedError()
