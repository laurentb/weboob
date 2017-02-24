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

from collections import OrderedDict
import re
import hashlib
from urlparse import urlparse
from html2text import unescape
from datetime import date, timedelta

from weboob.capabilities.bank import Account
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.pages import FormNotFound
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import ChaoticDateGuesser, LinearDateGuesser
from weboob.exceptions import BrowserHTTPError, ActionNeeded
from weboob.browser.filters.standard import CleanText

from .pages import (
    HomePage, LoginPage, LoginErrorPage, AccountsPage,
    SavingsPage, TransactionsPage, AdvisorPage, UselessPage,
    CardsPage, LifeInsurancePage, MarketPage, LoansPage, PerimeterPage,
    ChgPerimeterPage, MarketHomePage, FirstVisitPage, BGPIPage,
    TransferInit, TransferPage, ProfilePage,
)


__all__ = ['Cragr']


class WebsiteNotSupported(Exception):
    pass


class Cragr(LoginBrowser):
    home_page = URL(HomePage)
    login_page = URL(r'/stb/entreeBam$',
                     r'/stb/entreeBam\?.*typeAuthentification=CLIC_ALLER.*',
                     LoginPage)

    first_visit = URL(r'/stb/entreeBam\?.*pagePremVisite.*', FirstVisitPage)
    useless = URL(r'/stb/entreeBam\?.*Interstitielle.*',
                  r'/stb/entreeBam\?.*act=Tdbgestion',
                  r'/stb/entreeBam\?.*act=Messagesprioritaires',
                  r'https://.*/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect',
                  r'https://assurance-personnes.credit-agricole.fr/filiale/entreeBam\?actCrt=Synthcomptes&sessionSAG=.*&stbpg=pagePU&act=&typeaction=reroutage_retour&site=BAMG2&stbzn=bnc',
                  r'/stb/entreeBam\?sessionSAG=.*&stbpg=pagePU&.*typeaction=reroutage_aller&.*',
                  r'https://assurance-personnes.credit-agricole.fr/filiale/ServletReroutageCookie',
                  UselessPage)

    accounts = URL(r'/stb/entreeBam\?.*act=Synthcomptes',
                   r'/stb/collecteNI\?.*sessionAPP=Synthcomptes.*indicePage=.*',
                   AccountsPage)

    loans = URL(r'/stb/entreeBam\?.*act=Synthcredits',
                r'/stb/collecteNI\?.*sessionAPP=Synthcredits.*indicePage=.*',
                LoansPage)

    savings = URL(r'/stb/entreeBam\?.*act=Synthepargnes',
                  r'/stb/collecteNI\?.*sessionAPP=Synthepargnes.*indicePage=.*',
                  SavingsPage)

    transactions = URL(r'/stb/.*act=Releves.*',
                       r'/stb/collecteNI\?.*sessionAPP=Releves.*',
                       TransactionsPage)

    advisor = URL(r'/stb/entreeBam\?.*act=Contact',
                  r'https://.*/vitrine/tracking/t/', AdvisorPage)
    profile = URL(r'/stb/entreeBam\?.*act=Coordonnees', ProfilePage)
    login_error = URL(r'/stb/.*/erreur/.*', LoginErrorPage)
    cards = URL(r'/stb/collecteNI\?.*fwkaction=Cartes.*',
                r'/stb/collecteNI\?.*sessionAPP=Cartes.*',
                r'/stb/collecteNI\?.*fwkaction=Detail.*sessionAPP=Cartes.*',
                CardsPage)

    market = URL(r'https?://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal\?nump=.*', MarketPage)
    market_home = URL(r'https?://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis', MarketHomePage)
    lifeinsurance = URL(r'https://assurance-personnes.credit-agricole.fr(:443)?/filiale/.*', LifeInsurancePage)
    bgpi = URL(r'https://bgpi-gestionprivee.credit-agricole.fr/bgpi/.*', BGPIPage)

    perimeter = URL(r'/stb/entreeBam\?.*act=Perimetre', PerimeterPage)
    chg_perimeter = URL(r'/stb/entreeBam\?.*act=ChgPerim.*', ChgPerimeterPage)

    transfer_init_page = URL(r'/stb/entreeBam\?sessionSAG=(?P<sag>[^&]+)&stbpg=pagePU&act=Virementssepa&stbzn=bnt&actCrt=Virementssepa', TransferInit)
    transfer_page = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', TransferPage)

    new_login_domain = []
    new_login = False

    def __init__(self, website, *args, **kwargs):
        super(Cragr, self).__init__(*args, **kwargs)

        if website in self.new_login_domain:
            domain = re.sub('^m\.', 'w2.', website)
            self.new_login = True
        else:
            domain = re.sub('^m\.', 'www.', website)

        self._sag = None  # updated while browsing

        self._urls = OrderedDict(self._urls)
        self.home_site = 'https://%s/' % domain
        self.home_page = URL(self.home_site, self.home_site + 'particuliers.html', HomePage)
        self.home_page.browser = self
        self._urls['home_page'] = self.home_page

        self.accounts_url = None
        self.savings_url = None
        self._old_sag = None
        self.code_caisse = None  # constant for a given website
        self.perimeters = None
        self.current_perimeter = None
        self.broken_perimeters = list()

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self._sag = None

        if not self.home_page.is_here():
            self.home_page.go()

        if self.new_login:
            self.page.go_to_auth()
            parsed = urlparse(self.url)
            self.BASEURL = '%s://%s' % (parsed.scheme, parsed.netloc)
        else:
            # On the homepage, we get the URL of the auth service.
            url = self.page.get_post_url()
            if url is None:
                raise WebsiteNotSupported()

            # First, post account number to get the password prompt.
            data = {'CCPTE':                self.username[:11].encode('iso8859-15'),
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

            parsed = urlparse(url)
            self.BASEURL = '%s://%s' % (parsed.scheme, parsed.netloc)
            self.location(url, data=data)

        assert self.login_page.is_here()

        # Then, post the password.
        self.page.login(self.username, self.password)

        if self.new_login:
            url = self.page.get_accounts_url()
        else:
            # The result of POST is the destination URL.
            url = self.page.get_result_url()

        if not url.startswith('http'):
            raise BrowserIncorrectPassword(unescape(url, unicode_snob=True))

        self.location(url.replace('Synthese', 'Synthcomptes'))

        if self.login_error.is_here():
            raise BrowserIncorrectPassword()

        if self.page is None:
            raise WebsiteNotSupported()

        if not self.accounts.is_here():
            # Sometimes the home page is Releves.
            new_url  = re.sub('act=([^&=]+)', 'act=Synthcomptes', self.page.url, 1)
            self.location(new_url)

        if not self.accounts.is_here():
            raise BrowserIncorrectPassword()

        if self.code_caisse is None:
            self.code_caisse = self.page.get_code_caisse()

        # Store the current url to go back when requesting accounts list.
        self.accounts_url = re.sub('sessionSAG=[^&]+', 'sessionSAG={0}', self.page.url)

        # we can deduce the URL to "savings" and "loan" accounts from the regular accounts one
        self.savings_url  = re.sub('act=([^&=]+)', 'act=Synthepargnes', self.accounts_url, 1)
        self.loans_url  = re.sub('act=([^&=]+)', 'act=Synthcredits', self.accounts_url, 1)
        self.advisor_url  = re.sub('act=([^&=]+)', 'act=Contact', self.accounts_url, 1)
        self.profile_url  = re.sub('act=([^&=]+)', 'act=Coordonnees', self.accounts_url, 1)

        if self.page.check_perimeters() and not self.broken_perimeters:
            self.perimeter_url = re.sub('act=([^&=]+)', 'act=Perimetre', self.accounts_url, 1)
            self.chg_perimeter_url = '%s%s' % (re.sub('act=([^&=]+)', 'act=ChgPerim', self.accounts_url, 1), '&typeaction=ChgPerim')
            self.location(self.perimeter_url.format(self.sag))
            self.page.check_multiple_perimeters()

    @need_login
    def go_perimeter(self, perimeter):
        # If this fails, there is no point in retrying with same cookies.
        self.location(self.perimeter_url.format(self.sag))
        if self.page.get_error() is not None:
            self.do_login()
            self.location(self.perimeter_url.format(self.sag))
        if len(self.perimeters) > 2:
            perimeter_link = self.page.get_perimeter_link(perimeter)
            if perimeter_link:
                self.location(perimeter_link)
        self.location(self.chg_perimeter_url.format(self.sag))
        if self.page.get_error() is not None:
            self.broken_perimeters.append(perimeter)

    @need_login
    def get_accounts_list(self):
        l = list()
        if self.perimeters:
            for perimeter in [p for p in self.perimeters if p not in self.broken_perimeters]:
                if (self.page and not self.page.get_current()) or self.current_perimeter != perimeter:
                    self.go_perimeter(perimeter)
                for account in self.get_list():
                    if not account in l:
                        l.append(account)
        else:
            l = self.get_list()
        return l

    @need_login
    def get_cards_or_card(self, account_id=None):
        accounts = []
        if not self.accounts.is_here():
            self.location(self.accounts_url.format(self.sag))

        for idelco in self.page.cards_idelco_or_link():
            if not self.accounts.is_here():
                self.location(self.accounts_url.format(self.sag))
            self.location(self.page.cards_idelco_or_link(idelco))
            assert self.cards.is_here()
            for account in self.page.get_list():
                if account_id and account.number == account_id:
                    return account
                else:
                    accounts.append(account)

        return accounts

    @need_login
    def get_list(self):
        accounts_list = []
        # regular accounts
        if not self.accounts.is_here():
            self.location(self.accounts_url.format(self.sag))
        accounts_list.extend(self.page.get_list())

        # credit cards
        # reseting location in case of pagination
        self.location(self.accounts_url.format(self.sag))
        accounts_list.extend(self.get_cards_or_card())

        # loan accounts
        self.location(self.loans_url.format(self.sag))
        if self.loans.is_here():
            for account in self.page.get_list():
                if account not in accounts_list:
                    accounts_list.append(account)

        # savings accounts
        self.location(self.savings_url.format(self.sag))
        if self.savings.is_here():
            for account in self.page.get_list():
                if account not in accounts_list:
                    accounts_list.append(account)

        # update market accounts
        for account in accounts_list:
            if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
                try:
                    new_location = self.moveto_market_website(account, home=True)
                except WebsiteNotSupported:
                    account._link = None
                    self.update_sag()
                else:
                    self.location(new_location)
                    self.page.update(accounts_list)
                    self.quit_market_website()
                    break

        return accounts_list

    @need_login
    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    @need_login
    def get_history(self, account):
        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            self.logger.warning('This account is not supported')
            raise NotImplementedError()

        # some accounts may exist without a link to any history page
        if account._link is None or 'CATITRES' in account._link:
            return

        if account._perimeter != self.current_perimeter:
            self.go_perimeter(account._perimeter)

        # card accounts need to get an updated link
        if account.type == Account.TYPE_CARD:
            account = self.get_cards_or_card(account.number)

        if account.type != Account.TYPE_CARD or not self.page.is_on_right_detail(account):
            self.location(account._link.format(self.sag))

        if self.cards.is_here():
            date_guesser = ChaoticDateGuesser(date.today()-timedelta(weeks=36))
            url = self.page.url
            state = None
            notfirst = False
            while url:
                if notfirst:
                    self.location(url)
                else:
                    notfirst = True
                assert self.cards.is_here()
                for state, tr in self.page.get_history(date_guesser, state):
                    yield tr

                url = self.page.get_next_url()

        elif self.page:
            date_guesser = LinearDateGuesser()
            self.page.order_transactions()
            while True:
                assert self.transactions.is_here()

                for tr in self.page.get_history(date_guesser):
                    yield tr

                url = self.page.get_next_url()
                if url is None:
                    break
                self.location(url)

    @need_login
    def iter_investment(self, account):
        if not account._link or account.type not in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            return

        if account._perimeter != self.current_perimeter:
            self.go_perimeter(account._perimeter)

        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            new_location = self.moveto_market_website(account)
            # Detail unavailable
            try:
                self.location(new_location)
            except BrowserHTTPError:
                return
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            new_location = self.moveto_insurance_website(account)
            self.location(new_location, data={})
            if self.bgpi.is_here():
                if not self.page.go_detail():
                    return
            if self.lifeinsurance.is_here():
                self.page.go_on_detail(account.id)

        for inv in self.page.iter_investment():
            yield inv

        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            self.quit_market_website()
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            self.quit_insurance_website()

    @need_login
    def iter_advisor(self):
        if not self.advisor.is_here():
            self.location(self.advisor_url.format(self.sag))

        # it looks like we have an advisor only on cmds
        if "ca-cmds" in self.home_site:
            perimetre, agence = self.page.get_codeperimetre().split('-')
            publickey = self.location(self.home_site + '/Vitrine/jsp/CMDS/b.js').page.get_publickey()
            self.location("%svitrine/tracking/t/%s-%s.html" % (self.home_site.replace("www.ca", "www.credit-agricole"),
                                                               hashlib.sha1(perimetre + publickey).hexdigest(),
                                                               agence))
            yield self.page.get_advisor()
        # for other we take numbers
        else:
            for adv in self.page.iter_numbers():
                yield adv

    @need_login
    def get_profile(self):
        if not self.profile.is_here():
            self.location(self.profile_url.format(self.sag))

        return self.page.get_profile()

    @need_login
    def moveto_market_website(self, account, home=False):
        response = self.open(account._link % self.sag).text
        self._sag = None
        # https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.navigation.AccueilBridge?TOKEN_ID=
        m = re.search('document.location="([^"]+)"', response)
        if m:
            url = m.group(1)
        else:
            self.logger.warn('Unable to go to market website')
            raise WebsiteNotSupported()

        self.open(url)
        if home:
            return 'https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis'
        parsed = urlparse(url)
        url = '%s://%s/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal?nump=%s:%s'
        return url % (parsed.scheme, parsed.netloc, account.id, self.code_caisse)

    @need_login
    def quit_market_website(self):
        parsed = urlparse(self.url)
        exit_url = '%s://%s/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect' % (parsed.scheme, parsed.netloc)
        page = self.open(exit_url).page
        try:
            form = page.get_form(name='formulaire')
        except FormNotFound:
            msg = CleanText(u'//b[contains(text() , "Nous vous invitons à créer un mot de passe trading.")]')(self.page.doc)
            if msg:
                raise ActionNeeded(msg)
        else:
            # 'act' parameter allows page recognition, this parameter is ignored by
            # server
            self.location(form.url + '&act=Synthepargnes')

        self.update_sag()

    @need_login
    def moveto_insurance_website(self, account):
        page = self.open(account._link % self.sag).page
        self._sag = None
        # POST to https://assurance-personnes.credit-agricole.fr/filiale/ServletReroutageCookie
        try:
            form = page.get_form(name='formulaire')
        except FormNotFound:
            # bgpi-gestionprivee.
            body = self.open(account._link % self.sag).text
            return re.search('location="([^"]+)"', body, flags=re.MULTILINE).group(1)

        data = {
            'page': form['page'],
            'cMaxAge': '-1',
        }

        # TODO create a dedicated page and move this piece to page
        script = page.doc.find('//script').text
        for value in ('cMaxAge', 'cName', 'cValue'):
            m = re.search('%s.value *= *"([^"]+)"' % value, script)
            if m:
                data[value] = m.group(1)
            else:
                raise WebsiteNotSupported()

        page = self.open(form.url, data=data).page
        # POST to https://assurance-personnes.credit-agricole.fr:443/filiale/entreeBam?identifiantBAM=xxx
        form = page.get_form(name='formulaire')
        return form.url

    @need_login
    def quit_insurance_website(self):
        if self.bgpi.is_here():
            return self.page.go_back()
        exit_url = 'https://assurance-personnes.credit-agricole.fr/filiale/entreeBam?actCrt=Synthcomptes&sessionSAG=%s&stbpg=pagePU&act=&typeaction=reroutage_retour&site=BAMG2&stbzn=bnc'
        doc = self.open(exit_url % self.sag).page.doc
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

    @need_login
    def update_sag(self):
        script = self.page.doc.xpath("//script[contains(.,'idSessionSag =')]")
        if script:
            self._old_sag = self._sag = re.search('idSessionSag = "([^"]+)";', script[0].text).group(1)
        else:
            self._sag = self._old_sag

    @need_login
    def iter_transfer_recipients(self, account):
        self.transfer_init_page.go(sag=self.sag)
        for rcpt in self.page.iter_emitters():
            if rcpt.id == account.id:
                break
        else:
            # couldn't find the account as emitter
            return

        for rcpt in self.page.iter_recipients():
            if rcpt.iban or rcpt.id != account.id:
                yield rcpt

    @need_login
    def init_transfer(self, transfer, **params):
        accounts = self.get_accounts_list()

        assert transfer.recipient_id
        assert transfer.account_id

        self.transfer_init_page.go(sag=self.sag)
        assert self.transfer_init_page.is_here()

        currency = transfer.currency or 'EUR'
        if not isinstance(currency, basestring):
            # sometimes it's a Currency object
            currency = currency.id

        self.page.submit_accounts(transfer.account_id, transfer.recipient_id, transfer.amount, currency)

        assert self.page.is_reason()
        self.page.submit_more(transfer.label, transfer.exec_date)

        assert self.page.is_confirm()
        res = self.page.get_transfer()

        if not res.account_iban:
            for acc in accounts:
                self.logger.warning('%r %r', res.account_id, acc.id)
                if res.account_id == acc.id:
                    res.account_iban = acc.iban
                    break

        if not res.recipient_iban:
            for acc in accounts:
                if res.recipient_id == acc.id:
                    res.recipient_iban = acc.iban
                    break

        return res

    @need_login
    def execute_transfer(self, transfer, **params):
        assert self.transfer_page.is_here()
        assert self.page.is_confirm()
        self.page.submit_confirm()

        assert self.page.is_sent()
        return self.page.get_transfer()
