# -*- coding: utf-8 -*-

# Copyright(C) 2013  Romain Bignon
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


import re
import urllib
from urlparse import urlparse

from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser

from .pages import HomePage, LoginPage, LoginErrorPage, AccountsPage, \
                   SavingsPage, TransactionsPage, UselessPage, CardsPage, \
                   LifeInsurancePage, MarketPage, LoansPage


__all__ = ['Cragr']


class Cragr(Browser):
    PROTOCOL = 'https'
    ENCODING = 'ISO-8859-1'

    PAGES = {'https?://[^/]+/':                                          HomePage,
             'https?://[^/]+/stb/entreeBam':                             LoginPage,
             'https?://[^/]+/stb/entreeBam\?.*typeAuthentification=CLIC_ALLER.*': LoginPage,
             'https?://[^/]+/stb/entreeBam\?.*pagePremVisite.*':         UselessPage,
             'https?://[^/]+/stb/entreeBam\?.*Interstitielle.*':         UselessPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Tdbgestion':           UselessPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthcomptes':         AccountsPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthcredits':         LoansPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthepargnes':        SavingsPage,
             'https?://[^/]+/stb/.*act=Releves.*':                       TransactionsPage,
             'https?://[^/]+/stb/collecteNI\?.*sessionAPP=Releves.*':    TransactionsPage,
             'https?://[^/]+/stb/.*/erreur/.*':                          LoginErrorPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Messagesprioritaires': UselessPage,
             'https?://[^/]+/stb/collecteNI\?.*fwkaction=Cartes.*':      CardsPage,
             'https?://[^/]+/stb/collecteNI\?.*fwkaction=Detail.*sessionAPP=Cartes.*': CardsPage,
             'https?://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal\?nump=.*': MarketPage,
             'https://assurance-personnes.credit-agricole.fr:443/filiale/entreeBam\?identifiantBAM=.*': LifeInsurancePage,
            }

    class WebsiteNotSupported(Exception):
        pass

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = re.sub('^m\.', 'www.', website)
        self.accounts_url = None
        self.savings_url = None
        self._sag = None  # updated while browsing
        self.code_caisse = None  # constant for a given website
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.login()

    def is_logged(self):
        return self.page is not None and not self.is_on_page(HomePage) and self.page.get_error() is None

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        # Do we really need to login?
        if self.is_logged():
            self.logger.debug('already logged in')
            return

        self._sag = None

        if not self.is_on_page(HomePage):
            self.location(self.absurl('/'), no_login=True)

        # On the homepage, we get the URL of the auth service.
        url = self.page.get_post_url()
        if url is None:
            raise self.WebsiteNotSupported()

        # First, post account number to get the password prompt.
        data = {'CCPTE':                self.username.encode(self.ENCODING),
                'canal':                'WEB',
                'hauteur_ecran':        768,
                'largeur_ecran':        1024,
                'liberror':             '',
                'matrice':              'true',
                'origine':              'vitrine',
                'situationTravail':     'BANCAIRE',
                'typeAuthentification': 'CLIC_ALLER',
                'urlOrigine':           self.page.url,
                'vitrine':              0,
               }

        self.location(url, urllib.urlencode(data))

        assert self.is_on_page(LoginPage)

        # Then, post the password.
        self.page.login(self.password)

        # The result of POST is the destination URL.
        url = self.page.get_result_url()

        if not url.startswith('http'):
            raise BrowserIncorrectPassword(url)

        self.location(url)

        if self.is_on_page(LoginErrorPage):
            raise BrowserIncorrectPassword()

        if self.page is None:
            raise self.WebsiteNotSupported()

        if not self.is_on_page(AccountsPage):
            # Sometimes the home page is Releves.
            new_url  = re.sub('act=([^&=]+)', 'act=Synthcomptes', self.page.url, 1)
            self.location(new_url)

        if not self.is_on_page(AccountsPage):
            raise self.WebsiteNotSupported()

        if self.code_caisse is None:
            scripts = self.page.document.xpath('//script[contains(., " codeCaisse")]')
            self.code_caisse = re.search('var +codeCaisse *= *"([0-9]+)"', scripts[0].text).group(1)

        # Store the current url to go back when requesting accounts list.
        self.accounts_url = re.sub('sessionSAG=[^&]+', 'sessionSAG={0}', self.page.url)

        # we can deduce the URL to "savings" and "loan" accounts from the regular accounts one
        self.savings_url  = re.sub('act=([^&=]+)', 'act=Synthepargnes', self.accounts_url, 1)
        self.loans_url  = re.sub('act=([^&=]+)', 'act=Synthcredits', self.accounts_url, 1)

    def get_accounts_list(self):
        accounts_list = []
        # regular accounts
        if not self.is_on_page(AccountsPage):
            self.location(self.accounts_url.format(self.sag))
        accounts_list.extend(self.page.get_list())

        # credit cards
        for cards_page in self.page.cards_pages():
            self.location(cards_page)
            assert self.is_on_page(CardsPage)
            accounts_list.extend(self.page.get_list())

        # loan accounts
        self.location(self.loans_url.format(self.sag))
        if self.is_on_page(LoansPage):
            for account in self.page.get_list():
                if account not in accounts_list:
                    accounts_list.append(account)

        # savings accounts
        self.location(self.savings_url.format(self.sag))
        if self.is_on_page(SavingsPage):
            for account in self.page.get_list():
                if account not in accounts_list:
                    accounts_list.append(account)
        return accounts_list

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    def get_history(self, account):
        if account.type in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE):
            self.logger.warning('This account is not supported')
            return

        # some accounts may exist without a link to any history page
        if account._link is None:
            return

        # card accounts need to get an updated link
        if account.type == Account.TYPE_CARD:
            account = self.get_account(account.id)

        date_guesser = LinearDateGuesser()
        self.location(account._link.format(self.sag))

        if self.is_on_page(CardsPage):
            for tr in self.page.get_history(date_guesser):
                yield tr
        else:
            url = self.page.get_order_by_date_url()

            while url:
                self.location(url)
                assert self.is_on_page(TransactionsPage)

                for tr in self.page.get_history(date_guesser):
                    yield tr

                url = self.page.get_next_url()

    def iter_investment(self, account):
        if not account._link or account.type not in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE):
            self.logger.warning('This account is not supported')
            return

        if account.type == Account.TYPE_MARKET:
            new_location = self.moveto_market_website(account)
            self.location(new_location)
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            new_location = self.moveto_insurance_website(account)
            self.location(new_location, urllib.urlencode({}))

        for inv in self.page.iter_investment():
            yield inv

        if account.type == Account.TYPE_MARKET:
            self.quit_market_website()
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            self.quit_insurance_website()

    def moveto_market_website(self, account):
        response = self.openurl(account._link % self.sag).read()
        self._sag = None
        # https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.navigation.AccueilBridge?TOKEN_ID=
        m = re.search('document.location="([^"]+)"', response)
        if m:
            url = m.group(1)
        else:
            self.logger.warn('Unable to go to market website')
            raise self.WebsiteNotSupported()

        self.openurl(url)
        parsed = urlparse(url)
        url = '%s://%s/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal?nump=%s:%s'
        return url % (parsed.scheme, parsed.netloc, account.id, self.code_caisse)

    def quit_market_website(self):
        parsed = urlparse(self.geturl())
        exit_url = '%s://%s/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect' % (parsed.scheme, parsed.netloc)
        doc = self.get_document(self.openurl(exit_url), encoding='utf-8')
        form = doc.find('//form[@name="formulaire"]')
        # 'act' parameter allows page recognition, this parameter is ignored by
        # server
        self.location(form.attrib['action'] + '&act=Synthepargnes')

        self.update_sag()

    def moveto_insurance_website(self, account):
        doc = self.get_document(self.openurl(account._link % self.sag), encoding='utf-8')
        self._sag = None
        # POST to https://assurance-personnes.credit-agricole.fr/filiale/ServletReroutageCookie
        form = doc.find('//form[@name="formulaire"]')
        data = {
            'page': form.inputs['page'].attrib['value'],
            'cMaxAge': '-1',
        }
        script = doc.find('//script').text
        for value in ('cMaxAge', 'cName', 'cValue'):
            m = re.search('%s.value *= *"([^"]+)"' % value, script)
            if m:
                data[value] = m.group(1)
            else:
                raise self.WebsiteNotSupported()

        doc = self.get_document(self.openurl(form.attrib['action'], urllib.urlencode(data)), encoding='utf-8')

        # POST to https://assurance-personnes.credit-agricole.fr:443/filiale/entreeBam?identifiantBAM=xxx
        form = doc.find('//form[@name="formulaire"]')
        return form.attrib['action']

    def quit_insurance_website(self):
        exit_url = 'https://assurance-personnes.credit-agricole.fr/filiale/entreeBam?actCrt=Synthcomptes&sessionSAG=%s&stbpg=pagePU&act=&typeaction=reroutage_retour&site=BAMG2&stbzn=bnc'
        doc = self.get_document(self.openurl(exit_url % self.sag), encoding='utf-8')
        form = doc.find('//form[@name="formulaire"]')
        # 'act' parameter allows page recognition, this parameter is ignored by
        # server
        self.location(form.attrib['action'] + '&act=Synthepargnes')
        self.update_sag()

    @property
    def sag(self):
        if not self._sag:
            self.update_sag()
        return self._sag

    def update_sag(self):
        if not self.is_logged():
            self.login()

        script = self.page.document.xpath("//script[contains(.,'idSessionSag =')]")
        self._sag = re.search('idSessionSag = "([^"]+)";', script[0].text).group(1)
