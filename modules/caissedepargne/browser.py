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
import urlparse
import re

from weboob.browser import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.capabilities.bank import Account
from weboob.capabilities.profile import Profile
from weboob.browser.exceptions import BrowserHTTPNotFound, ClientError
from weboob.exceptions import BrowserIncorrectPassword

from .pages import IndexPage, ErrorPage, MarketPage, LifeInsurance, GarbagePage, \
                   MessagePage, LoginPage, CenetLoginPage, CenetHomePage, \
                   CenetAccountsPage, CenetAccountHistoryPage, CenetCardsPage, \
                   TransferPage, ProTransferPage, TransferConfirmPage, TransferSummaryPage


__all__ = ['CaisseEpargne']


class CaisseEpargne(LoginBrowser):
    BASEURL = "https://www.caisse-epargne.fr"

    login = URL('/authentification/manage\?step=identification&identifiant=(?P<login>.*)',
                'https://.*/login.aspx', LoginPage)
    account_login = URL('/authentification/manage\?step=account&identifiant=(?P<login>.*)&account=(?P<accountType>.*)', LoginPage)
    cenet_login = URL('https://www.cenet.caisse-epargne.fr/$', CenetLoginPage)
    cenet_home = URL('https://www.cenet.caisse-epargne.fr/Default.aspx$', CenetHomePage)
    cenet_accounts = URL('https://www.cenet.caisse-epargne.fr/Web/Api/ApiComptes.asmx/ChargerSyntheseComptes', CenetAccountsPage)
    cenet_account_history = URL('https://www.cenet.caisse-epargne.fr/Web/Api/ApiComptes.asmx/ChargerHistoriqueCompte', CenetAccountHistoryPage)
    cenet_account_coming = URL('https://www.cenet.caisse-epargne.fr/Web/Api/ApiCartesBanquaires.asmx/ChargerEnCoursCarte', CenetAccountHistoryPage)
    cenet_cards = URL('https://www.cenet.caisse-epargne.fr/Web/Api/ApiCartesBanquaires.asmx/ChargerCartes', CenetCardsPage)
    transfer = URL('https://.*/Portail.aspx.*', TransferPage)
    transfer_summary = URL('https://.*/Portail.aspx.*', TransferSummaryPage)
    transfer_confirm = URL('https://.*/Portail.aspx.*', TransferConfirmPage)
    pro_transfer = URL('https://.*/Portail.aspx.*', ProTransferPage)
    home = URL('https://.*/Portail.aspx.*', IndexPage)
    home_tache = URL('https://.*/Portail.aspx\?tache=(?P<tache>).*', IndexPage)
    error = URL('https://.*/login.aspx',
                'https://.*/Pages/logout.aspx.*',
                'https://.*/particuliers/Page_erreur_technique.aspx.*', ErrorPage)
    market = URL('https://.*/Pages/Bourse.*',
                 'https://www.caisse-epargne.offrebourse.com/ReroutageSJR',
                 'https://www.caisse-epargne.offrebourse.com/Portefeuille.*', MarketPage)
    life_insurance = URL('https://.*/Assurance/Pages/Assurance.aspx',
                         'https://www.extranet2.caisse-epargne.fr.*', LifeInsurance)
    message = URL('https://www.caisse-epargne.offrebourse.com/DetailMessage\?refresh=O', MessagePage)
    garbage = URL('https://www.caisse-epargne.offrebourse.com/Portefeuille',
                  'https://www.caisse-epargne.fr/particuliers/.*/emprunter.aspx',
                  'https://.*/particuliers/emprunter.*',
                  'https://.*/particuliers/epargner.*', GarbagePage)

    def __init__(self, nuser, *args, **kwargs):
        self.BASEURL = kwargs.pop('domain', self.BASEURL)
        if not self.BASEURL.startswith('https://'):
            self.BASEURL = 'https://%s' % self.BASEURL

        self.is_cenet_website = False
        self.multi_type = False
        self.accounts = None
        self.loans = None
        self.typeAccount = 'WE'
        self.nuser = nuser

        super(CaisseEpargne, self).__init__(*args, **kwargs)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        # Reset domain to log on pro website if first login attempt failed on personal website.
        if self.multi_type:
            self.BASEURL = 'https://www.caisse-epargne.fr'
            self.typeAccount = 'WP'

        data = self.login.go(login=self.username).get_response()

        if data is None:
            raise BrowserIncorrectPassword()

        if "authMode" in data and data['authMode'] == 'redirect':
            self.is_cenet_website = True

            post_data = {
                'CodeEtablissement': data['codeCaisse'],
                'NumeroBad': self.username,
                'NumeroUtilisateur': self.nuser
            }

            self.location(data['url'], data=post_data, headers={'Referer': 'https://www.cenet.caisse-epargne.fr/'})

            return self.page.login(self.username, self.password, self.nuser, data['codeCaisse'])

        if len(data['account']) > 1:
            self.multi_type = True
            data = self.account_login.go(login=self.username, accountType=self.typeAccount).get_response()

        assert data is not None

        typeAccount = data['account'][0]

        playload = {
            'auth_mode': 'ajax',
            'nuusager': self.nuser.encode('utf-8'),
            'codconf': self.password,
            'typeAccount': typeAccount,
            'step': 'authentification',
            'nuabbd': self.username
        }

        response = self.location(data['url'], params=playload).page.get_response()

        assert response is not None

        if not response['action']:
            if not self.typeAccount == 'WP' and self.multi_type:
                # If we haven't test PRO espace we check before raising wrong pass
                self.do_login()
                return
            raise BrowserIncorrectPassword(response['error'])

        self.BASEURL = urlparse.urljoin(data['url'], '/')

        try:
            self.home.go()
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        if self.accounts is None:
            # cenet website
            if self.is_cenet_website is True:
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
                    account._cards = [card for card in self.cenet_cards.go(data=json.dumps(data), headers=headers).get_cards() \
                                    if card['Compte']['Numero'] == account.id]
            else:
                if self.home.is_here():
                    self.page.check_no_accounts()
                    self.page.go_list()
                else:
                    self.home.go()

                self.accounts = list(self.page.get_list())
                for account in self.accounts:
                    if account.type == Account.TYPE_MARKET:
                        if not self.home.is_here():
                            self.home_tache.go(tache='CPTSYNT0')
                        self.page.go_history(account._info)

                        if self.message.is_here():
                            self.page.submit()
                            self.page.go_history(account._info)

                        # Some users may not have access to this.
                        if not self.market.is_here():
                            continue

                        self.page.submit()

                        if self.page.is_error():
                            continue

                        self.garbage.go()

                        if self.garbage.is_here():
                            continue
                        self.page.get_valuation_diff(account)
        return iter(self.accounts)

    @need_login
    def get_loans_list(self):
        if self.loans is None:
            self.loans = []
            if self.is_cenet_website is True:
                return iter([])

            if self.home.is_here():
                if self.page.check_no_accounts():
                    return iter([])

            self.home_tache.go(tache='CRESYNT0')

            if self.home.is_here():
                self.page.go_loan_list()
                self.loans = list(self.page.get_loan_list())

            for _ in range(3):
                try:
                    self.home_tache.go(tache='CPTSYNT0')

                    if self.home.is_here():
                        self.page.go_list()
                except ClientError:
                    pass
                else:
                    break

        return iter(self.loans)

    @need_login
    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()

        for a in l:
            if a.id == id:
                return a

        return None

    @need_login
    def _get_history(self, info):
        if isinstance(info['link'], list):
            info['link'] = info['link'][0]
        if not info['link'].startswith('HISTORIQUE'):
            return
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home_tache.go(tache='CPTSYNT0')

        self.page.go_history(info)

        info['link'] = [info['link']]
        if info['type'] == "HISTORIQUE_CB":
            info['link'] += self.page.get_cbtabs()

        while True:
            for i, link in enumerate(info['link'], 1):
                if i > 1:
                    info['link'] = link
                    self.page.go_history(info, True)

                assert self.home.is_here()

                for tr in self.page.get_history():
                    yield tr

                if not self.page.go_next():
                    return

    @need_login
    def _get_history_invests(self, account):
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()

        self.page.go_history(account._info)

        try:
            self.page.go_life_insurance(account)

            if self.market.is_here() is False and self.message.is_here() is False:
                return iter([])

            self.page.submit()
            self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_histo())
        except (IndexError, AttributeError) as e:
            self.logger.error(e)
            return iter([])
        return self.page.iter_history()

    @need_login
    def get_history(self, account):
        if self.is_cenet_website is True:
            # cenet website
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
            while True:
                self.cenet_account_history.go(data=json.dumps(data), headers=headers)
                for tr in self.page.get_history():
                    items.append(tr)

                offset = self.page.next_offset()
                if not offset:
                    break

                data['filtreEntree'] = json.dumps({
                    'Offset': offset,
                })

            return items
        if not hasattr(account, '_info'):
            raise NotImplementedError
        if account.type is Account.TYPE_LIFE_INSURANCE:
            return self._get_history_invests(account)
        return self._get_history(account._info)

    @need_login
    def get_coming(self, account):
        trs = []

        if self.is_cenet_website is True:
            # cenet website
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
        else:
            if not hasattr(account, '_info'):
                raise NotImplementedError()
            for info in account._card_links:
                for tr in self._get_history(info.copy()):
                    tr.type = tr.TYPE_DEFERRED_CARD
                    tr.nopurge = True
                    trs.append(tr)

        return iter(sorted(trs, key=lambda t: t.rdate, reverse=True))

    @need_login
    def get_investment(self, account):
        if self.is_cenet_website is True:
            # not available for the moment
            return iter([])

        if account.type is not Account.TYPE_LIFE_INSURANCE and account.type is not Account.TYPE_MARKET:
            raise NotImplementedError()
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()

        self.page.go_history(account._info)
        if account.type is Account.TYPE_MARKET:
            # Some users may not have access to this.
            if not self.market.is_here():
                return iter([])
            self.page.submit()
            if self.page.is_error():
                return iter([])
            self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille')
            if self.message.is_here():
                return iter([])
            if not self.page.is_on_right_portfolio(account):
                self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille?compte=%s' % self.page.get_compte(account))
        elif account.type is Account.TYPE_LIFE_INSURANCE:
            try:
                self.page.go_life_insurance(account)

                if self.market.is_here() is False and self.message.is_here() is False:
                    return iter([])

                self.page.submit()
                self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_repart())
            except (IndexError, AttributeError) as e:
                self.logger.error(e)
                return iter([])
        if self.garbage.is_here():
            return iter([])
        return self.page.iter_investment()

    @need_login
    def get_advisor(self):
        if not self.is_cenet_website:
            raise NotImplementedError()

        return iter([self.cenet_home.stay_or_go().get_advisor()])

    @need_login
    def get_profile(self):
        if not self.is_cenet_website:
            profile = Profile()
            profile.name = unicode(re.search('nomusager=([^&]+)', self.session.cookies['headerdei']).group(1))
        else:
            profile = self.cenet_home.stay_or_go().get_profile()
        return profile

    @need_login
    def iter_recipients(self, origin_account):
        if self.is_cenet_website is True:
            # not available for the moment
            return iter([])
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()
        self.page.go_transfer()
        if not self.page.can_transfer(origin_account):
            return iter([])
        return self.page.iter_recipients(account_id=origin_account.id)

    @need_login
    def init_transfer(self, account, recipient, transfer):
        if self.is_cenet_website is True:
            # not available for the moment
            raise NotImplementedError()
        if self.home.is_here():
            self.page.go_list()
        else:
            self.home.go()
        self.page.go_transfer()
        if self.pro_transfer.is_here():
            raise NotImplementedError()

        self.page.init_transfer(account, recipient, transfer)
        self.page.continue_transfer(account.label, recipient, transfer.label)
        return self.page.create_transfer(account, recipient, transfer)

    @need_login
    def execute_transfer(self, transfer):
        self.page.confirm()
        return self.page.populate_reference(transfer)
