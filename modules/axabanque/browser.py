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

from .pages.login import KeyboardPage, LoginPage, PredisconnectedPage
from .pages.bank import AccountsPage as BankAccountsPage, CBTransactionsPage, \
                        TransactionsPage, UnavailablePage, IbanPage
from .pages.wealth import AccountsPage as WealthAccountsPage, InvestmentPage, HistoryPage


class AXABrowser(LoginBrowser):
    # Login
    keyboard = URL('https://connect.axa.fr/keyboard/password', KeyboardPage)
    login = URL('https://connect.axa.fr/api/identity/auth', LoginPage)
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
            accounts.extend(list(self.wealth_accounts.go().iter_accounts()))
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
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            invs = []
            # do we still need it ?...
            if account._acctype == "bank" and account._hasinv:
                self.go_account_pages(account, "investment")
                invs = list(self.page.iter_investment())
            elif account._acctype == "investment":
                investment_link = self.location(account._link).page.get_investment_link()
                invs = list(self.location(investment_link).page.iter_investment())
            self.cache['invs'][account.id] = invs
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        # Side investment's website
        if account._acctype == "investment":
            pagination_link = self.location(self.wealth_accounts.urls[0][:-1] + account._link).page.get_pagination_link()
            self.location(pagination_link, params={'skip': 0})
            self.skip = 0
            for tr in self.page.iter_history(pagination_link=pagination_link):
                yield tr
        # Main website withouth investments
        elif account._acctype == "bank" and not account._hasinv:
            self.go_account_pages(account, "history")
            if self.page.more_history():
                for tr in self.page.get_history():
                    yield tr


class AXAAssurance(AXABrowser):
    BASEURL = 'https://espaceclient.axa.fr'

    accounts = URL('/accueil.html', WealthAccountsPage)
    investment = URL('/content/ecc-popin-cards/savings/(\w+)/repartition', InvestmentPage)
    history = URL('.*accueil/savings/(\w+)/contract', HistoryPage)

    def __init__(self, *args, **kwargs):
        super(AXAAssurance, self).__init__(*args, **kwargs)
        self.cache = {}
        self.cache['invs'] = {}

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.cache['accs'] = list(self.accounts.stay_or_go().iter_accounts())
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            investment_link = self.location(account._link).page.get_investment_link()
            self.cache['invs'][account.id] = list(self.location(investment_link).page.iter_investment())
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        pagination_link = self.location(account._link).page.get_pagination_link()
        self.location(pagination_link, params={'skip': 0})
        self.skip = 0
        for tr in self.page.iter_history(pagination_link=pagination_link):
            yield tr
