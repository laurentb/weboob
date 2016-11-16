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
import mechanize
from urlparse import urlsplit

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.bank import Account
from weboob.browser.exceptions import BrowserHTTPNotFound

from .pages import IndexPage, ErrorPage, UnavailablePage, MarketPage, LifeInsurance, GarbagePage, MessagePage


__all__ = ['CaisseEpargne']


class CaisseEpargne(Browser):
    DOMAIN = 'www.caisse-epargne.fr'
    PROTOCOL = 'https'
    CERTHASH = ['9a5af08c31a22a0dbc2724cec14ce9b1f8e297571c046c2210a16fa3a9f8fc2e', '0e0fa585a8901c206c4ebbc7ee33e00e17809d7086f224e1b226c46165a4b5ac',
                '8f8b9e1de4b3ae16128105cb0759a1afeaaedbd18957afa390738390fec3c30d']
    PAGES = {'https://[^/]+/Portail.aspx.*':                              IndexPage,
             'https://[^/]+/login.aspx':                                  ErrorPage,
             'https://[^/]+/Pages/logout.aspx.*':                         ErrorPage,
             'https://[^/]+/particuliers/Page_erreur_technique.aspx.*':   ErrorPage,
             'https://[^/]+/page_hs_dei_.*.aspx':                         UnavailablePage,
             'https://[^/]+/Pages/Bourse.*':                              MarketPage,
             'https://www.caisse-epargne.offrebourse.com/ReroutageSJR':   MarketPage,
             'https://www.caisse-epargne.offrebourse.com/Portefeuille.*': MarketPage,
             'https://[^/]+/Assurance/Pages/Assurance.aspx':              LifeInsurance,
             'https://www.extranet2.caisse-epargne.fr.*':                 LifeInsurance,
             'https://www.caisse-epargne.offrebourse.com/DetailMessage\?refresh=O': MessagePage,
             'https://www.caisse-epargne.fr/particuliers/.*/emprunter.aspx': GarbagePage,
             'https://.*/particuliers/emprunter.*':                       GarbagePage,
             'https://.*/particuliers/epargner.*':                        GarbagePage,
            }

    def __init__(self, nuser, *args, **kwargs):
        self.multi_type = False
        self.typeAccount = 'WE'
        self.nuser = nuser
        self.DOMAIN = kwargs.pop('domain', self.DOMAIN)
        Browser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page is not None and not self.is_on_page(ErrorPage)

    def home(self):
        if self.is_logged():
            self.location(self.buildurl('/Portail.aspx'))
        else:
            self.login()

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.is_logged():
            return

        # Reset domain to log on pro website if first login attempt failed on personal website.
        if self.multi_type:
            self.DOMAIN = 'www.caisse-epargne.fr'
            self.typeAccount = 'WP'

        response = self.openurl('/authentification/manage?step=identification&identifiant=%s' % self.username)
        try:
            data = json.loads(response.get_data())
        except ValueError:
            raise BrowserIncorrectPassword('Mot de passe incorrect')
        # In case there are multiple spaces, currently choose by default the
        # personal one.
        if len(data['account']) > 1:
            self.multi_type = True
            response = self.openurl('/authentification/manage?step=account&identifiant=%s&account=%s' % (self.username, self.typeAccount))
            data = json.loads(response.get_data())

        typeAccount = data['account'][0]
        response = self.openurl(self.buildurl(data['url'],
                                              ('auth_mode', 'ajax'),
                                              ('nuusager', self.nuser.encode('utf-8')),
                                              ('codconf', self.password),
                                              ('typeAccount', typeAccount),
                                              ('step', 'authentification'),
                                              ('nuabbd', self.username)))
        try:
            json_response = json.loads(response.get_data())
            if not json_response['action']:
                if not self.typeAccount == 'WP' and self.multi_type:
                    # If we haven't test PRO espace we check before raising wrong pass
                    self.login()
                    return
                raise BrowserIncorrectPassword(json_response['error'])
        except ValueError:
            raise BrowserUnavailable()
        v = urlsplit(response.geturl())
        self.DOMAIN = v.netloc
        try:
            self.location('/Portail.aspx', nologin=self.multi_type)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword('Identifiant incorrect')

        if not self.is_logged():
            raise BrowserUnavailable()

    def get_accounts_list(self):
        if self.is_on_page(IndexPage):
            self.page.check_no_accounts()
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx'))

        accounts = list(self.page.get_list())
        for account in accounts:
            if account.type == Account.TYPE_MARKET:
                if not self.is_on_page(IndexPage):
                    self.location(self.buildurl('/Portail.aspx?tache=CPTSYNT0'))

                self.page.go_history(account._info)
                if self.is_on_page(MessagePage):
                    self.page.submit()
                    self.page.go_history(account._info)
                # Some users may not have access to this.
                if not self.is_on_page(MarketPage):
                    continue
                self.page.submit()
                if self.page.is_error():
                    continue
                self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille')
                if self.is_on_page(GarbagePage):
                    continue
                self.page.get_valuation_diff(account)
        return iter(accounts)

    def get_loans_list(self):
        if self.is_on_page(IndexPage):
            if self.page.check_no_accounts():
                return iter([])
        self.location(self.buildurl('/Portail.aspx?tache=CRESYNT0'))
        loan_accounts = list()
        if self.is_on_page(IndexPage):
            self.page.go_loan_list()
            loan_accounts = list(self.page.get_loan_list())
        for _ in range(3):
            try:
                self.location(self.absurl('/Portail.aspx?tache=CPTSYNT0'))
                if self.is_on_page(IndexPage):
                    self.page.go_list()
            except mechanize.BrowserStateError:
                pass
            else:
                break
        return(loan_accounts)


    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def _get_history(self, info):
        if not info['link'].startswith('HISTORIQUE'):
            return
        if self.is_on_page(IndexPage):
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx?tache=CPTSYNT0'))

        self.page.go_history(info)

        info['link'] = [info['link']]
        if info['type'] == "HISTORIQUE_CB":
            info['link'] += self.page.get_cbtabs()

        while True:
            for i, link in enumerate(info['link'], 1):
                if i > 1:
                    info['link'] = link
                    self.page.go_history(info, True)

                assert self.is_on_page(IndexPage)

                for tr in self.page.get_history():
                    yield tr

                if not self.page.go_next():
                    return

    def _get_history_invests(self, account):
        if self.is_on_page(IndexPage):
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx'))

        self.page.go_history(account._info)

        try:
            self.page.go_life_insurance(account)
            self.page.submit()
            self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_histo())
        except (IndexError, AttributeError) as e:
            self.logger.error(e)
            return iter([])
        return self.page.iter_history()

    def get_history(self, account):
        if not hasattr(account, '_info'):
            raise NotImplementedError()
        if account.type is Account.TYPE_LIFE_INSURANCE:
            return self._get_history_invests(account)
        return self._get_history(account._info)

    def get_coming(self, account):
        if not hasattr(account, '_info'):
            raise NotImplementedError()
        trs = []
        for info in account._card_links:
            for tr in self._get_history(info.copy()):
                tr.type = tr.TYPE_DEFERRED_CARD
                tr.nopurge = True
                trs.append(tr)
        return iter(sorted(trs, key=lambda t: t.rdate, reverse=True))

    def get_investment(self, account):
        if account.type is not Account.TYPE_LIFE_INSURANCE and account.type is not Account.TYPE_MARKET:
            raise NotImplementedError()
        if self.is_on_page(IndexPage):
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx'))

        self.page.go_history(account._info)
        if account.type is Account.TYPE_MARKET:
            # Some users may not have access to this.
            if not self.is_on_page(MarketPage):
                return iter([])
            self.page.submit()
            if self.page.is_error():
                return iter([])
            self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille')
            if self.is_on_page(MessagePage):
                return iter([])
            if not self.page.is_on_right_portfolio(account):
                self.location('https://www.caisse-epargne.offrebourse.com/Portefeuille?compte=%s' % self.page.get_compte(account))
        elif account.type is Account.TYPE_LIFE_INSURANCE:
            try:
                self.page.go_life_insurance(account)
                self.page.submit()
                self.location('https://www.extranet2.caisse-epargne.fr%s' % self.page.get_cons_repart())
            except (IndexError, AttributeError) as e:
                self.logger.error(e)
                return iter([])
        if self.is_on_page(GarbagePage):
            return iter([])
        return self.page.iter_investment()
