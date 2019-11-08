# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
from datetime import timedelta, date
from lxml.etree import XMLSyntaxError
from collections import OrderedDict

from weboob.tools.date import LinearDateGuesser
from weboob.capabilities.bank import Account, AccountNotFound, AccountOwnership
from weboob.tools.capabilities.bank.transactions import sorted_transactions, keep_only_card_transactions
from weboob.tools.compat import parse_qsl, urlparse
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import HTTPNotFound
from weboob.capabilities.base import find_object

from .pages.account_pages import (
    AccountsPage, OwnersListPage, CBOperationPage, CPTOperationPage, LoginPage,
    AppGonePage, RibPage, UnavailablePage, OtherPage, FrameContainer, ProfilePage, ScpiHisPage
)
from .pages.life_insurances import (
    LifeInsurancesPage, LifeInsurancePortal, LifeInsuranceMain, LifeInsuranceUseless,
    LifeNotFound,
)
from .pages.investments import (
    LogonInvestmentPage, ProductViewHelper, RetrieveAccountsPage, RetrieveInvestmentsPage,
    RetrieveLiquidityPage, RetrieveUselessPage, ScpiInvestmentPage,
)
from .pages.landing_pages import JSMiddleFramePage, JSMiddleAuthPage, InvestmentFormPage


__all__ = ['HSBC']


class HSBC(LoginBrowser):
    BASEURL = 'https://client.hsbc.fr'

    app_gone = False

    scpi_investment_page = URL(r'https://www.hsbc.fr/1/[0-9]/.*', ScpiInvestmentPage)
    scpi_his_page = URL(r'https://www.hsbc.fr/1/[0-9]/.*', ScpiHisPage)
    connection = URL(r'https://www.hsbc.fr/1/2/hsbc-france/particuliers/connexion', LoginPage)
    login = URL(r'https://www.hsbc.fr/1/*', LoginPage)
    cptPage = URL(
        r'/cgi-bin/emcgi.*\&Cpt=.*',
        r'/cgi-bin/emcgi.*\&Epa=.*',
        r'/cgi-bin/emcgi.*\&CPT_IdPrestation.*',
        r'/cgi-bin/emcgi.*\&Ass_IdPrestation.*',
        # FIXME are the previous patterns relevant in POST nav?
        r'/cgi-bin/emcgi',
        CPTOperationPage,
    )
    cbPage = URL(
        r'/cgi-bin/emcgi.*[\&\?]Cb=.*',
        r'/cgi-bin/emcgi.*\&CB_IdPrestation.*',
        # FIXME are the previous patterns relevant in POST nav?
        r'/cgi-bin/emcgi',
        CBOperationPage,
    )
    appGone = URL(
        r'/.*_absente.html',
        r'/pm_absent_inter.html',
        r'/appli_absente_MBEL.html',
        r'/pm_absent_inter_MBEL.html',
        AppGonePage,
    )
    rib = URL(r'/cgi-bin/emcgi', RibPage)
    accounts = URL(r'/cgi-bin/emcgi', AccountsPage)
    owners_list = URL(r'/cgi-bin/emcgi', OwnersListPage)
    life_insurance_useless = URL(r'/cgi-bin/emcgi', LifeInsuranceUseless)
    profile = URL(r'/cgi-bin/emcgi', ProfilePage)
    unavailable = URL(r'/cgi-bin/emcgi', UnavailablePage)
    frame_page = URL(
        r'/cgi-bin/emcgi',
        r'https://clients.hsbc.fr/cgi-bin/emcgi',
        FrameContainer,
    )

    # other site
    life_insurance_portal = URL(r'/cgi-bin/emcgi', LifeInsurancePortal)
    life_insurance_main = URL(r'https://assurances.hsbc.fr/fr/accueil/b2c/accueil.html\?pointEntree=PARTIEGENERIQUEB2C', LifeInsuranceMain)
    life_insurances = URL(r'https://assurances.hsbc.fr/navigation', LifeInsurancesPage)
    life_not_found = URL(r'https://assurances.hsbc.fr/fr/404.html', LifeNotFound)

    # investment pages
    middle_frame_page = URL(r'/cgi-bin/emcgi', JSMiddleFramePage)
    middle_auth_page = URL(r'/cgi-bin/emcgi', JSMiddleAuthPage)
    investment_form_page = URL(
        r'https://www.hsbc.fr/1/[0-9]/authentication/sso-cwd\?customerFullName=.*',
        InvestmentFormPage
    )
    logon_investment_page = URL(
        r'https://investissements.clients.hsbc.fr/group-wd-gateway-war/gateway/LogonAuthentication',
        r'https://investissements.clients.hsbc.fr/cwd/group-wd-gateway-war/gateway/LogonAuthentication',
        LogonInvestmentPage
    )
    retrieve_accounts_view = URL(
        r'https://investissements.clients.hsbc.fr/cwd/group-wd-gateway-war/gateway/wd/RetrieveCustomerPortfolio',
        RetrieveAccountsPage
    )
    retrieve_investments_page = URL(
        r'https://investissements.clients.hsbc.fr/cwd/group-wd-gateway-war/gateway/wd/RetrieveCustomerPortfolio',
        RetrieveInvestmentsPage
    )
    retrieve_liquidity_page = URL(
        r'https://investissements.clients.hsbc.fr/cwd/group-wd-gateway-war/gateway/wd/RetrieveCustomerPortfolio',
        RetrieveLiquidityPage
    )
    retrieve_useless_page = URL(
        r'https://investissements.clients.hsbc.fr/cwd/group-wd-gateway-war/gateway/wd/RetrieveCustomerPortfolio',
        RetrieveUselessPage
    )

    # catch-all
    other_page = URL(r'/cgi-bin/emcgi', OtherPage)

    def __init__(self, username, password, secret, *args, **kwargs):
        super(HSBC, self).__init__(username, password, *args, **kwargs)
        self.accounts_dict = OrderedDict()
        self.unique_accounts_dict = dict()
        self.secret = secret
        self.PEA_LISTING = {}
        self.owners_url_list = []
        self.web_space = None
        self.home_url = None

    def load_state(self, state):
        return

    def do_login(self):
        self.session.cookies.clear()

        self.app_gone = False
        self.connection.go()
        self.page.login(self.username)

        no_secure_key_link = self.page.get_no_secure_key()

        if not no_secure_key_link:
            raise BrowserIncorrectPassword()
        self.location(no_secure_key_link)

        self.page.login_w_secure(self.password, self.secret)
        for _ in range(3):
            if self.login.is_here():
                self.page.useless_form()

        # This wonderful website has 2 baseurl with only one difference: the 's' at the end of 'client'
        new_base_url = 'https://clients.hsbc.fr/'
        if new_base_url in self.url:
            self.BASEURL = new_base_url

        if self.frame_page.is_here():
            self.home_url = self.page.get_frame()
            self.js_url = self.page.get_js_url()

        if not self.home_url or not self.page.logged:
            raise BrowserIncorrectPassword()

        self.location(self.home_url)

    def go_post(self, url, data=None):
        # most of HSBC accounts links are actually handled by js code
        # which convert a GET query string to POST data.
        # not doing so often results in logout by the site
        q = dict(parse_qsl(urlparse(url).query))
        if data:
            q.update(data)
        url = url[:url.find('?')]
        self.location(url, data=q)

    def go_to_owner_accounts(self, owner):
        """
        The owners URLs change all the time so we must refresh them.
        If we try to go to a person's accounts page while we are already
        on this page, the website returns an empty page with the message
        "Pas de TIERS", so we must always go to the owners list before
        going to the owner's account page.
        """

        if not self.owners_list.is_here():
            self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})

        if not self.owners_list.is_here():
            # Sometimes when we fetch info from a PEA account, the first POST
            # fails and we are blocked on some owner's AccountsPage.
            self.logger.warning('The owners list redirection failed, we must try again.')
            self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})

        # Refresh owners URLs in case they changed:
        self.owners_url_list = self.page.get_owners_urls()
        self.go_post(self.owners_url_list[owner])

    @need_login
    def iter_account_owners(self):
        """
        Some connections have a "Compte de Tiers" section with several
        people each having their own accounts. We must fetch the account
        for each person and store the owner of each account.
        """
        if not self.web_space:
            if not self.accounts.is_here():
                self.location(self.home_url)
            self.web_space = self.page.get_web_space()

        if not self.unique_accounts_dict and self.web_space == 'new_space':
            self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})  # Go to the owners list to find the list of other owners
            self.owners_url_list = self.page.get_owners_urls()

            for owner in range(len(self.owners_url_list)):
                self.accounts_dict[owner] = {}
                self.update_accounts_dict(owner)

                # We must set an "_owner" attribute to each account.
                for a in self.accounts_dict[owner].values():
                    a._owner = owner

                    # The first space is the PSU owner space
                    if owner == 0:
                        a.ownership = AccountOwnership.OWNER
                    else:
                        a.ownership = AccountOwnership.ATTORNEY

                # go on cards page if there are cards accounts
                for a in self.accounts_dict[owner].values():
                    if a.type == Account.TYPE_CARD:
                        self.location(a.url)
                        break

                # get all couples (card, parent) on card page
                all_card_and_parent = []
                if self.cbPage.is_here():
                    all_card_and_parent = self.page.get_all_parent_id()
                    self.go_post(self.js_url, data={'debr': 'COMPTES_PAN'})

                # update cards parent and currency
                for a in self.accounts_dict[owner].values():
                    if a.type == Account.TYPE_CARD:
                        for card in all_card_and_parent:  # card[0] and card[1] are labels containing the id for the card and its parents account, respectively
                            if a.id in card[0].replace(' ', ''):  # cut spaces in labels such as 'CARTE PREMIER N° 1234 00XX XXXX 5678'
                                parent_id = re.match(r'^(\d*)?(\d{11}EUR)$', card[1]).group(2)  # ids in the HTML have 5 numbers added at the beginning, catch only the end
                                a.parent = find_object(self.accounts_dict[owner].values(), id=parent_id)
                            if a.parent and not a.currency:
                                a.currency = a.parent.currency

                # We must get back to the owners list before moving to the next owner:
                self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})

            # Fill a dictionary will all accounts without duplicating common accounts:
            for owner in self.accounts_dict.values():
                for account in owner.values():
                    if account.id not in self.unique_accounts_dict.keys():
                        self.unique_accounts_dict[account.id] = account
                    else:
                        # If an account is in multiple space, that's mean it is shared between this owners.
                        self.unique_accounts_dict[account.id].ownership = AccountOwnership.CO_OWNER

        if self.unique_accounts_dict:
            for account in self.unique_accounts_dict.values():
                yield account
        else:
            # TODO ckeck GrayLog and get rid of old space code if clients are no longer using it
            self.logger.warning('Passed through the old HSBC webspace')
            self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})
            self.owners_url_list = self.page.get_owners_urls()

            # self.accounts_dict will be a dictionary of owners each
            # containing a dictionary of the owner's accounts.
            for owner in range(len(self.owners_url_list)):
                self.accounts_dict[owner] = {}
                self.update_accounts_dict(owner)

                # We must set an "_owner" attribute to each account.
                for a in self.accounts_dict[owner].values():
                    a._owner = owner

                # go on cards page if there are cards accounts
                for a in self.accounts_dict[owner].values():
                    if a.type == Account.TYPE_CARD:
                        self.location(a.url)
                        break

                # get all couples (card, parent) on cards page
                all_card_and_parent = []
                if self.cbPage.is_here():
                    all_card_and_parent = self.page.get_all_parent_id()
                    self.go_post(self.js_url, data={'debr': 'COMPTES_PAN'})

                # update cards parent and currency
                for a in self.accounts_dict[owner].values():
                    if a.type == Account.TYPE_CARD:
                        for card in all_card_and_parent:
                            if a.id in card[0].replace(' ', ''):
                                a.parent = find_object(self.accounts_dict[owner].values(), id=card[1])
                            if a.parent and not a.currency:
                                a.currency = a.parent.currency

                # We must get back to the owners list before moving to the next owner:
                self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})

            # Fill a dictionary will all accounts without duplicating common accounts:
            for owner in self.accounts_dict.values():
                for account in owner.values():
                    if account.id not in self.unique_accounts_dict.keys():
                        self.unique_accounts_dict[account.id] = account
            for account in self.unique_accounts_dict.values():
                yield account

    @need_login
    def update_accounts_dict(self, owner, iban=True):
        # Go to the owner's account page in case we are not there already:
        self.go_to_owner_accounts(owner)

        for a in self.page.iter_spaces_account(self.web_space):
            try:
                self.accounts_dict[owner][a.id].url = a.url
            except KeyError:
                self.accounts_dict[owner][a.id] = a

        if iban:
            self.location(self.js_url, params={'debr': 'COMPTES_RIB'})
            if self.rib.is_here():
                self.page.get_rib(self.accounts_dict[owner])

    @need_login
    def _quit_li_space(self):
        if self.life_insurances.is_here():
            self.page.disconnect()

            self.session.cookies.pop('ErisaSession', None)
            self.session.cookies.pop('HBFR-INSURANCE-COOKIE-82', None)

        if self.life_not_found.is_here():
            # likely won't avoid having to login again anyway
            self.location(self.js_url)

        if self.frame_page.is_here():
            home_url = self.page.get_frame()
            self.js_url = self.page.get_js_url()

            self.location(home_url)

        if self.life_insurance_useless.is_here():
            data = {'debr': 'COMPTES_PAN'}
            self.go_post(self.js_url, data=data)

    @need_login
    def _go_to_life_insurance(self, account):
        self._quit_li_space()
        self.go_post(account.url)

        if self.accounts.is_here() or self.frame_page.is_here() or self.life_insurance_useless.is_here() or self.life_not_found.is_here():
            self.logger.warning('cannot go to life insurance %r', account)
            return False

        data = {'url_suivant': 'SITUATIONCONTRATB2C', 'strNumAdh': ''}
        data.update(self.page.get_lf_attributes(account.id))

        self.life_insurances.go(data=data)
        return True

    @need_login
    def get_history(self, account, coming=False, retry_li=True):
        self._quit_li_space()
        #  Update accounts list only in case of several owners
        if len(self.owners_url_list) > 1:
            self.update_accounts_dict(account._owner, iban=False)
        account = self.accounts_dict[account._owner][account.id]

        if account.url is None:
            return []

        if account.url.startswith('javascript') or '&Crd=' in account.url or account.type == Account.TYPE_LOAN:
            raise NotImplementedError()

        if account.type == Account.TYPE_MARKET and 'BOURSE_INV' not in account.url:
            # Clean account url
            m = re.search(r"'(.*)'", account.url)
            if m:
                account_url = m.group(1)
            else:
                account_url = account.url
            # Need to be on accounts page to go on scpi page
            self.accounts.go()
            # Go on scpi page
            self.location(account_url)
            self.location(self.page.go_scpi_his_detail_page())

            return self.page.iter_history()

        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_CAPITALISATION):
            if coming is True:
                return []

            try:
                if not self._go_to_life_insurance(account):
                    self._quit_li_space()
                    return []
            except (XMLSyntaxError, HTTPNotFound):
                self._quit_li_space()
                return []
            except AccountNotFound:
                self.go_post(self.js_url)

                # often if we visit life insurance subsite multiple times too quickly, the site just returns an error
                # so we just retry (we might relogin...)
                # TODO find out how to avoid the error, or avoid relogin
                if retry_li:
                    self.logger.warning('life insurance seems unavailable for account %s', account.id)
                    return self.get_history(account, coming, False)

                self.logger.error('life insurance seems unavailable for account %s', account.id)
                return []

            self.life_insurances.go(data={'url_suivant': 'HISTORIQUECONTRATB2C', 'strMonnaie': 'EURO'})

            history = [t for t in self.page.iter_history()]

            self._quit_li_space()

            return history

        try:
            self.go_post(account.url)
        # sometime go to hsbc life insurance space do logout
        except HTTPNotFound:
            self.app_gone = True
            self.do_logout()
            self.do_login()
        # If we relogin on hsbc, all links have changed
        if self.app_gone:
            self.app_gone = False
            self.update_accounts_dict(account._owner, iban=False)
            self.location(self.accounts_dict[account._owner][account.id].url)

        if self.page is None:
            return []

        # for 'fusion' and 'new' space there is a form to submit on the page to go the account's history
        if hasattr(account, '_is_form') and account._is_form:
            # go on accounts page to get account form
            self.go_to_owner_accounts(account._owner)
            self.go_post(self.js_url, data={'debr': 'COMPTES_PAN'})
            self.page.go_history_page(account)

        if self.cbPage.is_here():
            history_tabs_urls = self.page.history_tabs_urls()
            guesser = LinearDateGuesser(date_max_bump=timedelta(45))
            history = []
            if coming:
                self.location(history_tabs_urls[0])  # fetch only first tab coming transactions
                history += list(self.page.get_history(date_guesser=guesser))
            else:
                for tab in history_tabs_urls[1:]:
                    self.location(tab)  # fetch all tab but first of past transactions
                    history += list(self.page.get_history(date_guesser=guesser))

            for tr in history:
                if tr.type == tr.TYPE_UNKNOWN:
                    tr.type = tr.TYPE_DEFERRED_CARD
                    tr.bdate = tr.rdate

            if account.parent:
                # Fetching the card summaries from the parent account using the card id in the transaction labels:
                def match_card(tr):
                    return (account.id in tr.label.replace(' ', ''))
                history.extend(keep_only_card_transactions(self.get_history(account.parent), match_card))

            history = [tr for tr in history if (coming and tr.date > date.today()) or (not coming and tr.date <= date.today())]
            history = sorted_transactions(history)
            return history
        elif not coming:
            return self._get_history()
        else:
            raise NotImplementedError()

    def _get_history(self):
        for tr in self.page.get_history():
            yield tr

    def get_investments(self, account, retry_li=True):
        if not account.url:
            raise NotImplementedError()
        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_CAPITALISATION):
            return self.get_life_investments(account, retry_li=retry_li)
        elif account.type == Account.TYPE_PEA:
            return self.get_pea_investments(account)
        elif account.type == Account.TYPE_MARKET:
            # 'BOURSE_INV' need more security to get invest page
            if 'BOURSE_INV' in account.url:
                return self.get_pea_investments(account)
            return self.get_scpi_investments(account)
        else:
            raise NotImplementedError()

    def get_scpi_investments(self, account):
        if not account.url:
            raise NotImplementedError()
        # Clean account url
        m = re.search(r"'(.*)'", account.url)
        if m:
            account_url = m.group(1)
        else:
            account_url = account.url

        # Need to be on accounts page to go on scpi page
        self.go_to_owner_accounts(account._owner)
        self.accounts.go()
        # Go on scpi page
        self.location(account_url)
        # Go on scpi details page
        self.page.go_scpi_detail_page()
        # If there is more details page, go on that page
        self.page.go_more_scpi_detail_page()
        return self.page.iter_scpi_investment()

    def get_pea_investments(self, account):
        self.go_to_owner_accounts(account._owner)
        assert account.type in (Account.TYPE_PEA, Account.TYPE_MARKET)

        # When invest balance is 0, there is not link to go on market page
        if not account.balance:
            return []

        if not self.PEA_LISTING:
            # _go_to_wealth_accounts returns True if everything went well.
            if not self._go_to_wealth_accounts(account):
                self.logger.warning('Unable to connect to wealth accounts.')
                return []

        # Get account number without "EUR"
        account_id = re.search(r'\d{4,}', account.id).group(0)
        pea_invests = []
        account = None

        if 'accounts' in self.PEA_LISTING:
            for acc in self.PEA_LISTING['accounts']:
                # acc.id is like XXX<account number>
                if account_id in acc.id:
                    account = acc
                    break
        # Account should be found
        assert account

        if 'liquidities' in self.PEA_LISTING:
            for liquidity in self.PEA_LISTING['liquidities']:
                if liquidity._invest_account_id == account.number:
                    pea_invests.append(liquidity)
        if 'investments' in self.PEA_LISTING:
            for invest in self.PEA_LISTING['investments']:
                if invest._invest_account_id == account.id:
                    pea_invests.append(invest)
        return pea_invests

    def get_life_investments(self, account, retry_li=True):
        self._quit_li_space()
        self.update_accounts_dict(account._owner, False)
        account = self.accounts_dict[account._owner][account.id]
        try:
            if not self._go_to_life_insurance(account):
                self._quit_li_space()
                return []
        except (XMLSyntaxError, HTTPNotFound):
            self._quit_li_space()
            return []
        except AccountNotFound:
            self.go_post(self.js_url)

            # often if we visit life insurance subsite multiple times too quickly, the site just returns an error
            # retry (we might relogin...)
            if retry_li:
                self.logger.warning('life insurance seems unavailable for account %s', account.id)
                return self.get_investments(account, False)

            self.logger.error('life insurance seems unavailable for account %s', account.id)
            return []

        investments = [i for i in self.page.iter_investments()]

        self._quit_li_space()

        return investments

    def _go_to_wealth_accounts(self, account):
        if not hasattr(self.page, 'get_middle_frame_url'):
            # if we can catch the URL, we go directly, else we need to browse
            # the website
            self.update_accounts_dict(account._owner, False)

        self.location(self.page.get_middle_frame_url())

        if self.page.get_patrimoine_url():
            self.location(self.page.get_patrimoine_url())
            self.page.go_next()

            if self.login.is_here():
                self.logger.warning('Connection to the Logon page failed, we must try again.')
                self.do_login()
                self.update_accounts_dict(account._owner, False)
                self.investment_form_page.go()
                # If reloggin did not help accessing the wealth space,
                # there is nothing more we can do to get there.
                if not self.investment_form_page.is_here():
                    return False

            self.page.go_to_logon()
            helper = ProductViewHelper(self)
            # we need to go there to initialize the session
            self.PEA_LISTING['accounts'] = list(helper.retrieve_accounts())
            self.PEA_LISTING['liquidities'] = list(helper.retrieve_liquidity())
            self.PEA_LISTING['investments'] = list(helper.retrieve_invests())
            self.connection.go()
            return True

    @need_login
    def get_profile(self):
        if not self.owners_url_list:
            self.go_post(self.js_url, data={'debr': 'OPTIONS_TIE'})
            if self.owners_list.is_here():
                self.owners_url_list = self.page.get_owners_urls()

        # The main owner of the connection is always the first of the list:
        self.go_to_owner_accounts(0)
        data = {'debr': 'PARAM'}
        self.go_post(self.js_url, data=data)
        return self.page.get_profile()
