# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ClientError
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded

from .pages.login import KeyboardPage, LoginPage, ChangepasswordPage, PredisconnectedPage
from .pages.bank import AccountsPage as BankAccountsPage, CBTransactionsPage, \
                        TransactionsPage, UnavailablePage, IbanPage, LifeInsuranceIframe
from .pages.wealth import AccountsPage as WealthAccountsPage, InvestmentPage, HistoryPage
from weboob.capabilities.bank import Account

class AXABrowser(LoginBrowser):
    # Login
    keyboard = URL('https://connect.axa.fr/keyboard/password', KeyboardPage)
    login = URL('https://connect.axa.fr/api/identity/auth', LoginPage)
    password = URL('https://connect.axa.fr/#/changebankpassword', ChangepasswordPage)
    predisconnected = URL('https://www.axa.fr/axa-predisconnect.html',
                          'https://www.axa.fr/axa-postmaw-predisconnect.html', PredisconnectedPage)

    def do_login(self):
        # due to the website change, login changed too, this is for don't try to login with the wrong login
        if self.username.isdigit() and len(self.username) > 7:
            raise ActionNeeded()

        if self.password.isdigit():
            vk_passwd = self.keyboard.go().get_password(self.password)

            login_data = {
                'email': self.username,
                'password': vk_passwd,
                'rememberIdenfiant': False,
                'version': 1
            }

            self.login.go(data=login_data)

        if not self.password.isdigit() or self.page.check_error():
            raise BrowserIncorrectPassword()

        # home page to finish login
        self.location('https://espaceclient.axa.fr/')


class AXABanque(AXABrowser):
    BASEURL = 'https://www.axabanque.fr/'

    # Bank
    bank_accounts = URL('transactionnel/client/liste-comptes.html',
                        'transactionnel/client/liste-(?P<tab>.*).html',
                        'webapp/axabanque/jsp/visionpatrimoniale/liste_panorama_.*\.faces',
                        r'/webapp/axabanque/page\?code=(?P<code>\d+)',
                        'webapp/axabanque/client/sso/connexion\?token=(?P<token>.*)', BankAccountsPage)
    iban_pdf = URL('http://www.axabanque.fr/webapp/axabanque/formulaire_AXA_Banque/.*\.pdf.*', IbanPage)
    cbttransactions = URL('webapp/axabanque/jsp/detailCarteBleu.*.faces', CBTransactionsPage)
    transactions = URL('webapp/axabanque/jsp/panorama.faces',
                       'webapp/axabanque/jsp/visionpatrimoniale/panorama_.*\.faces',
                       'webapp/axabanque/jsp/detail.*.faces',
                       'webapp/axabanque/jsp/.*/detail.*.faces', TransactionsPage)
    unavailable = URL('login_errors/indisponibilite.*',
                      '.*page-indisponible.html.*',
                      '.*erreur/erreurBanque.faces', UnavailablePage)
    # Wealth
    wealth_accounts = URL('https://espaceclient.axa.fr/$',
                          'https://connexion.adis-assurances.com', WealthAccountsPage)
    investment = URL('https://espaceclient.axa.fr/.*content/ecc-popin-cards/savings/(\w+)/repartition', InvestmentPage)
    history = URL('https://espaceclient.axa.fr/.*accueil/savings/(\w+)/contract',
                  'https://espaceclient.axa.fr/#', HistoryPage)

    lifeinsurance_iframe = URL('https://assurance-vie.axabanque.fr/Consultation/SituationContrat.aspx',
                               'https://assurance-vie.axabanque.fr/Consultation/HistoriqueOperations.aspx', LifeInsuranceIframe)

    def __init__(self, *args, **kwargs):
        super(AXABanque, self).__init__(*args, **kwargs)
        self.cache = {}
        self.cache['invs'] = {}

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            accounts = []
            ids = set()
            # Get accounts
            self.transactions.go()
            self.bank_accounts.go()
            # Ugly 3 loops : nav through all tabs and pages
            for tab in self.page.get_tabs():
                for page, page_args in self.bank_accounts.stay_or_go(tab=tab).get_pages(tab):
                    for a in page.get_list():
                        if a.id in ids:
                            # the "-comptes" page may return the same accounts as other pages, skip them
                            continue
                        ids.add(a.id)

                        #The url giving life insurrance investments seems to be temporary.
                        #That's why we have to get them now
                        if a.type == a.TYPE_LIFE_INSURANCE:
                            self.cache['invs'][a.id] = list(self.open(a._url).page.iter_investment())
                        args = a._args
                        # Trying to get IBAN for checking accounts
                        if a.type == a.TYPE_CHECKING and 'paramCodeFamille' in args:
                            iban_params = {'action': 'RIBCC',
                                           'numCompte': args['paramNumCompte'],
                                           'codeFamille': args['paramCodeFamille'],
                                           'codeProduit': args['paramCodeProduit'],
                                           'codeSousProduit': args['paramCodeSousProduit']
                                          }
                            try:
                                r = self.open('/webapp/axabanque/popupPDF', params=iban_params)
                                a.iban = r.page.get_iban()
                            except ClientError:
                                a.iban = NotAvailable
                        # Need it to get accounts from tabs
                        a._tab, a._pargs, a._purl = tab, page_args, self.url
                        accounts.append(a)
            # Get investment accounts if there has
            self.wealth_accounts.go()
            if self.wealth_accounts.is_here():
                accounts.extend(list(self.page.iter_accounts()))
            else:
                # it probably didn't work, go back on a regular page to avoid being logged out
                self.transactions.go()

            self.cache['accs'] = accounts
        return self.cache['accs']

    @need_login
    def go_account_pages(self, account, action):
        # Default to "comptes"
        tab = "comptes" if not hasattr(account, '_tab') else account._tab
        self.bank_accounts.go(tab=tab)
        args = account._args
        args['javax.faces.ViewState'] = self.page.get_view_state()
        # Nav for accounts in tab pages
        if tab != "comptes" and hasattr(account, '_url') \
                and hasattr(account, '_purl') and hasattr(account, '_pargs'):
            self.location(account._purl, data=account._pargs)
            self.location(account._url, data=args)
            # Check if we are on the good tab
            if isinstance(self.page, TransactionsPage):
                self.page.go_action(action)
        else:
            target = self.page.get_form_action(args['_form_name'])
            self.location(target, data=args)

    @need_login
    def go_wealth_pages(self, account):
        self.wealth_accounts.go()
        self.location(account.url)
        self.location(self.page.get_account_url(account.url))

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            # do we still need it ?...
            if account._acctype == "bank" and account._hasinv:
                self.go_account_pages(account, "investment")
            elif account._acctype == "investment":
                self.go_wealth_pages(account)
                investment_url = self.page.get_investment_url()
                if investment_url is None:
                    self.logger.warning('no investment link for account %s, returning empty', account)
                    # fake data, don't cache it
                    return []
                self.location(investment_url)
            self.cache['invs'][account.id] = list(self.page.iter_investment())
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        if account.type is Account.TYPE_LOAN:
            return

        if account.type == Account.TYPE_LIFE_INSURANCE and account._acctype == "bank":
            if not self.lifeinsurance_iframe.is_here():
                self.location(account._url)
            self.page.go_to_history()

            # Pass account investments to try to get isin code for transaction investments
            for tr in self.page.iter_history(investments=self.cache['invs'][account.id] if account.id in self.cache['invs'].iterkeys() else []):
                yield tr

        # Side investment's website
        if account._acctype == "investment":
            self.go_wealth_pages(account)
            pagination_url = self.page.get_pagination_url()
            self.location(pagination_url, params={'skip': 0})
            self.skip = 0
            for tr in self.page.iter_history(pagination_url=pagination_url):
                yield tr
        # Main website withouth investments
        elif account._acctype == "bank" and not account._hasinv and account.type != Account.TYPE_CARD:
            self.go_account_pages(account, "history")

            if self.page.more_history():
                for tr in self.page.get_history():
                    yield tr

    def iter_coming(self, account):
        if account._acctype == "bank" and account.type == Account.TYPE_CARD:
            self.go_account_pages(account, "history")

            if self.page.more_history():
                for tr in self.page.get_history():
                    yield tr


class AXAAssurance(AXABrowser):
    BASEURL = 'https://espaceclient.axa.fr'

    accounts = URL('/accueil.html', WealthAccountsPage)
    investment = URL('/content/ecc-popin-cards/savings/(\w+)/repartition', InvestmentPage)
    history = URL('.*accueil/savings/(\w+)/contract',
                  'https://espaceclient.axa.fr/#', HistoryPage)

    def __init__(self, *args, **kwargs):
        super(AXAAssurance, self).__init__(*args, **kwargs)
        self.cache = {}
        self.cache['invs'] = {}

    def go_wealth_pages(self, account):
        self.location("/" + account.url)
        self.location(self.page.get_account_url(account.url))

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.cache['accs'] = list(self.accounts.stay_or_go().iter_accounts())
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            self.go_wealth_pages(account)
            investment_url = self.page.get_investment_url()
            if investment_url is None:
                self.logger.warning('no investment link for account %s, returning empty', account)
                # fake data, don't cache it
                return []
            self.location(investment_url)
            self.cache['invs'][account.id] = list(self.page.iter_investment())
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        self.go_wealth_pages(account)
        pagination_url = self.page.get_pagination_url()
        self.location(pagination_url, params={'skip': 0})
        for tr in self.page.iter_history():
            yield tr
