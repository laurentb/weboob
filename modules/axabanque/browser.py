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

from .pages import KeyboardPage, LoginPage, PredisconnectedPage, BankAccountsPage, \
                   InvestmentPage, CBTransactionsPage, TransactionsPage, UnavailablePage, \
                   IbanPage


class AXABanque(LoginBrowser):
    BASEURL = 'https://www.axabanque.fr/'

    # Login
    keyboard = URL('https://connect.axa.fr/keyboard/password', KeyboardPage)
    login = URL('https://connect.axa.fr/api/identity/auth', LoginPage)
    predisconnected = URL('https://www.axa.fr/axa-predisconnect.html',
                          'https://www.axa.fr/axa-postmaw-predisconnect.html', PredisconnectedPage)
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
    # Investment
    investment = URL('https://espaceclient.axa.fr',
                     'https://connexion.adis-assurances.com', InvestmentPage)
    investment_transactions = URL('https://espaceclient.axa.fr/accueil/savings/savings/contract/_jcr_content/' + \
                                  'par/savingsmovementscard.savingscard.pid_(?P<pid>.*).aid_(?P<aid>.*).html\?skip=(?P<skip>.*)')

    def __init__(self, *args, **kwargs):
        super(AXABanque, self).__init__(*args, **kwargs)
        self.tokens = {}
        # Need to cache every pages, website is too slow
        self.account_list = []
        self.investment_list = {}
        self.history_list = {}

    def do_login(self):
        # due to the website change, login changed too, this is for don't try to login with the wrong login
        if len(self.username) > 7:
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


    @need_login
    def iter_accounts(self):
        if not self.account_list:
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
            self.investment.go()

            if self.investment.is_here():
                for a in self.page.iter_accounts():
                    accounts.append(a)

            self.account_list = accounts

        return iter(self.account_list)

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
    def iter_history(self, account):
        if account.id not in self.history_list:
            trs = []
            # Side investment's website
            if account._acctype == "investment":
                skip = 0

                try:
                    while self.investment_transactions.go(pid=account.id.zfill(16), aid=account._aid, skip=skip):
                        for a in self.page.iter_history():
                            trs.append(a)
                        skip += 10
                except AssertionError:
                    # assertion error when page is empty
                    pass

            # Main website withouth investments
            elif account._acctype == "bank" and not account._hasinv:
                self.go_account_pages(account, "history")
                if self.page.more_history():
                    trs = [a for a in self.page.get_history()]
            self.history_list[account.id] = trs
        return iter(self.history_list[account.id])

    @need_login
    def iter_investment(self, account):
        if account.id not in self.investment_list:
            invs = []
            if account._acctype == "bank" and account._hasinv:
                self.go_account_pages(account, "investment")
                invs = [i for i in self.page.iter_investment()]
            self.investment_list[account.id] = invs
        return iter(self.investment_list[account.id])
