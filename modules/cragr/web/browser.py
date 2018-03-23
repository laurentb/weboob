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

from __future__ import unicode_literals

import re
import hashlib
from html2text import unescape
from datetime import date, datetime, timedelta

from weboob.capabilities.bank import (
    Account, AddRecipientStep, AddRecipientError, RecipientInvalidLabel,
    Recipient, AccountNotFound,
)
from weboob.capabilities.base import NotLoaded, find_object
from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.browser.pages import FormNotFound
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import ChaoticDateGuesser, LinearDateGuesser
from weboob.exceptions import BrowserHTTPError, ActionNeeded
from weboob.browser.filters.standard import CleanText
from weboob.tools.value import Value
from weboob.tools.compat import urlparse, urljoin, basestring

from .pages import (
    HomePage, LoginPage, LoginErrorPage, AccountsPage,
    SavingsPage, TransactionsPage, AdvisorPage, UselessPage,
    CardsPage, LifeInsurancePage, MarketPage, LoansPage, PerimeterPage,
    ChgPerimeterPage, MarketHomePage, FirstVisitPage, BGPIPage,
    TransferInit, TransferPage, RecipientPage, RecipientListPage, ProfilePage,
    HistoryPostPage, RecipientMiscPage, DeferredCardsPage, UnavailablePage,
)


__all__ = ['Cragr']


class WebsiteNotSupported(Exception):
    pass


class Cragr(LoginBrowser, StatesMixin):
    home_page = URL('/$', '/particuliers.html', 'https://www.*.fr/Vitrine/jsp/CMDS/b.js', HomePage)
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
                r'/stb/collecteNI\?.*sessionAPP=Synthcredits.*',
                LoansPage)

    savings = URL(r'/stb/entreeBam\?.*act=Synthepargnes',
                  r'/stb/collecteNI\?.*sessionAPP=Synthepargnes.*indicePage=.*',
                  SavingsPage)

    transactions = URL(r'/stb/.*act=Releves.*',
                       r'/stb/collecteNI\?.*sessionAPP=Releves.*',
                       TransactionsPage)
    transactions_post = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', HistoryPostPage)

    advisor = URL(r'/stb/entreeBam\?.*act=Contact',
                  r'https://.*/vitrine/tracking/t/', AdvisorPage)
    profile = URL(r'/stb/entreeBam\?.*act=Coordonnees', ProfilePage)
    login_error = URL(r'/stb/.*/erreur/.*', LoginErrorPage)
    cards = URL(r'/stb/collecteNI\?.*fwkaction=Cartes.*',
                r'/stb/collecteNI\?.*sessionAPP=Cartes.*',
                r'/stb/collecteNI\?.*fwkaction=Detail.*sessionAPP=Cartes.*',
                CardsPage)
    cards2 = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', DeferredCardsPage)

    market = URL(r'https?://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal\?nump=.*', MarketPage)
    market_home = URL(r'https?://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis', MarketHomePage)
    lifeinsurance = URL(r'https://assurance-personnes.credit-agricole.fr/filiale/.*', LifeInsurancePage)
    bgpi = URL(r'https://bgpi-gestionprivee.credit-agricole.fr/bgpi/.*', BGPIPage)

    perimeter = URL(r'/stb/entreeBam\?.*act=Perimetre', PerimeterPage)
    chg_perimeter = URL(r'/stb/entreeBam\?.*act=ChgPerim.*', ChgPerimeterPage)

    transfer_init_page = URL(r'/stb/entreeBam\?sessionSAG=(?P<sag>[^&]+)&stbpg=pagePU&act=Virementssepa&stbzn=bnt&actCrt=Virementssepa', TransferInit)
    transfer_page = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', TransferPage)

    recipient_misc = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', RecipientMiscPage)
    recipientlist = URL(r'/stb/collecteNI\?.*&act=Vilistedestinataires.*', RecipientListPage)
    recipient_page = URL(r'/stb/collecteNI\?.*fwkaction=Ajouter.*', RecipientPage)

    unavailable_page = URL(r'/stb/collecteNI\?fwkaid=([\d_]+)&fwkpid=([\d_]+)$', UnavailablePage)

    new_login_domain = []
    new_login = False

    # the state is required for adding recipients: the sms code is linked to a cookie session
    __states__ = (
        'first_domain', 'BASEURL',
        'accounts_url', 'savings_url', 'loans_url', 'advisor_url', 'profile_url',
        'perimeter_url', 'chg_perimeter_url',
        'perimeters', 'broken_perimeters', 'code_caisse', '_sag', '_old_sag',
    )
    STATE_DURATION = 5

    def __init__(self, website, *args, **kwargs):
        super(Cragr, self).__init__(*args, **kwargs)

        if website in self.new_login_domain:
            self.first_domain = re.sub('^m\.', 'w2.', website)
            self.new_login = True
        else:
            self.first_domain = re.sub('^m\.', 'www.', website)

        self._sag = None  # updated while browsing

        self.accounts_url = None
        self.savings_url = None
        self._old_sag = None
        self.code_caisse = None  # constant for a given website
        self.perimeters = None
        self.current_perimeter = None
        self.broken_perimeters = list()
        self.BASEURL = 'https://%s/' % self.first_domain

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        self.BASEURL = 'https://%s/' % self.first_domain
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
    def get_card(self, id):
        return find_object(self.get_cards(), id=id)

    @need_login
    def get_cards(self):
        self.location(self.accounts_url.format(self.sag))

        for idelco in self.page.iter_idelcos():
            if not self.accounts.is_here():
                self.location(self.accounts_url.format(self.sag))

            obj = self.page.get_idelco(idelco)
            if isinstance(obj, basestring):
                self.location(obj)
            else:
                self.page.submit_card(obj)

            assert self.cards.is_here() or self.cards2.is_here()
            if self.page.several_cards():
                for account in self.page.iter_cards():
                    yield account
            else:
                for account in self.page.iter_card():
                    yield account


    @need_login
    def get_list(self):
        accounts_list = []
        # regular accounts
        self.location(self.accounts_url.format(self.sag))

        accounts_list.extend(self.page.iter_accounts())

        for account in accounts_list:
            self.location(self.accounts_url.format(self.sag))
            # after visiting any url/form, all other url/forms become invalid
            # so we need to go back to accounts list and get a new one each time
            updated_account = find_object(self.page.iter_accounts(), id=account.id)
            if updated_account.url:
                self.location(updated_account.url)
            elif account._form:
                self.location(updated_account._form.request)

            if updated_account.url or updated_account._form:
                iban_url = self.page.get_iban_url()
                if iban_url:
                    self.location(iban_url)
                    account.iban = self.page.get_iban()

        # credit cards
        # reseting location in case of pagination
        self.location(self.accounts_url.format(self.sag))
        accounts_list.extend(self.get_cards())

        # loan accounts
        self.location(self.loans_url.format(self.sag))
        if self.loans.is_here():
            for account in self.page.iter_loans():
                if account not in accounts_list:
                    if not account.type:
                        account.type = Account.TYPE_LOAN

                    accounts_list.append(account)

        # savings accounts
        self.location(self.savings_url.format(self.sag))
        if self.savings.is_here():
            for account in self.page.iter_accounts():
                if account not in accounts_list:
                    accounts_list.append(account)

        # update market accounts
        for account in accounts_list:
            if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA) and account.url:
                try:
                    new_location = self.moveto_market_website(account, home=True)
                except WebsiteNotSupported:
                    account.url = None
                    self.update_sag()
                else:
                    self.location(new_location)
                    for acc in self.page.get_list():
                        if account.id == acc.id:
                            account.balance = acc.balance or account.balance
                            account.label = acc.label or account.label
                    self.quit_market_website()
                    break

        # be sure that we send accounts with balance
        return [acc for acc in accounts_list if acc.balance is not NotLoaded]

    @need_login
    def get_history(self, account):
        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            self.logger.warning('This account is not supported')
            raise NotImplementedError()

        # some accounts may exist without a link to any history page
        if not account._form and (not account.url or 'CATITRES' in account.url):
            return

        if account._perimeter != self.current_perimeter:
            self.go_perimeter(account._perimeter)

        if account.type not in (Account.TYPE_LOAN, Account.TYPE_CARD) and account._form:
            # the account needs a form submission to go to the history
            # but we need to get the latest form data
            self.location(self.accounts_url.format(self.sag))
            accounts = self.page.iter_accounts()
            new_account = find_object(accounts, AccountNotFound, id=account.id)
            self.location(new_account._form.request)

        # card accounts need to get an updated link
        if account.type == Account.TYPE_CARD:
            account = self.get_card(account.id)

        if account.url and (account.type != Account.TYPE_CARD or not self.page.is_on_right_detail(account)):
            self.location(account.url.format(self.sag))

        if self.cards.is_here():
            date_guesser = ChaoticDateGuesser(date.today()-timedelta(weeks=42))
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
        if not account.url or account.type not in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
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
                if self.page.cgu_needed() or not self.page.go_detail():
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
        if "ca-cmds" in self.first_domain:
            perimetre, agence = self.page.get_codeperimetre().split('-')
            publickey = self.location(urljoin('https://' + self.first_domain, '/Vitrine/jsp/CMDS/b.js')).page.get_publickey()
            self.location(urljoin('https://' + self.first_domain.replace("www.ca", "www.credit-agricole"),
                                  "vitrine/tracking/t/%s-%s.html" % (hashlib.sha1(perimetre + publickey).hexdigest(),
                                                                     agence)))
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
        response = self.open(account.url % self.sag).text
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
        page = self.open(account.url % self.sag).page
        self._sag = None
        # POST to https://assurance-personnes.credit-agricole.fr/filiale/ServletReroutageCookie
        try:
            form = page.get_form(name='formulaire')
        except FormNotFound:
            # bgpi-gestionprivee.
            body = self.open(account.url % self.sag).text
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
        if account._perimeter != self.current_perimeter:
            self.go_perimeter(account._perimeter)

        self.transfer_init_page.go(sag=self.sag)

        if self.page.get_error() == 'Fonctionnalité Indisponible':
            self.location(self.accounts_url.format(self.sag))
            return

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
        accounts = list(self.get_accounts_list())

        assert transfer.recipient_id
        assert transfer.account_id

        account = find_object(accounts, id=transfer.account_id, error=AccountNotFound)
        if account._perimeter != self.current_perimeter:
            self.go_perimeter(account._perimeter)

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

    def build_recipient(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = recipient.category
        r.enabled_at = datetime.now().replace(microsecond=0)
        r.currency = u'EUR'
        r.bank_name = recipient.bank_name
        return r

    @need_login
    def new_recipient(self, recipient, **params):
        if not re.match(u"^[-+.,:/?() éèêëïîñàâäãöôòõùûüÿ0-9a-z']+$", recipient.label, re.I):
            raise RecipientInvalidLabel('Recipient label contains invalid characters')

        if 'sms_code' in params and not re.match(r'^[a-z0-9]{6}$', params['sms_code'], re.I):
            raise AddRecipientError('SMS verification code is invalid')

        self.transfer_init_page.go(sag=self.sag)
        self.location(self.page.url_list_recipients())
        self.location(self.page.url_add_recipient())

        if not ('sms_code' in params and self.page.can_send_code()):
            self.page.send_sms()
            # go to a GET page, so StatesMixin can reload it
            self.location(self.accounts_url.format(self.sag))
            raise AddRecipientStep(self.build_recipient(recipient), Value('sms_code', label='Veuillez saisir le code SMS'))
        else:
            self.page.submit_code(params['sms_code'])

            err = hasattr(self.page, 'get_sms_error') and self.page.get_sms_error()
            if err:
                raise AddRecipientError(message=err)

            self.page.submit_recipient(recipient.label, recipient.iban)
            self.page.confirm_recipient()
            self.page.check_recipient_error()

            res = self.page.find_recipient(recipient.iban)
            if res is None:
                raise AddRecipientError('Recipient could not be found')
            return res
