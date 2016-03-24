# -*- coding: utf-8 -*-

# Copyright(C) 2016       Baptiste Delpey
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

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, Field, TableCell, Regexp, Date, AsyncLoad, Async
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.value import Value
from weboob.exceptions import BrowserQuestion, BrowserIncorrectPassword


class BrowserAuthenticationCodeMaxLimit(BrowserIncorrectPassword):
    pass


class AuthenticationPage(HTMLPage):
    MAX_LIMIT = r"vous avez atteint le nombre maximum "\
        "d'utilisation de l'authentification forte."

    def authenticate(self):
        self.logger.info('Using the PIN Code %s to login', self.browser.config['pin_code'].get())
        self.logger.info('Using the auth_token %s to login', self.browser.auth_token)

        form = self.get_form()
        form['otp_confirm[otpCode]'] = self.browser.config['pin_code'].get()
        form['flow_secureForm_instance'] = self.browser.auth_token
        form['otp_confirm[validate]'] = ''
        form.submit()

        self.browser.auth_token = None

    def sms_first_step(self):
        """
        This function simulates the registration of a device on
        boursorama two factor authentification web page.
        @param device device name to register
        @exception BrowserAuthenticationCodeMaxLimit when daily limit is consumed
        """
        form = self.get_form()
        form.submit()

    def sms_second_step(self):
        form = self.get_form()
        self.browser.auth_token = form['flow_secureForm_instance']
        form['otp_prepare[receiveCode]'] = ''
        form.submit()

        raise BrowserQuestion(Value('pin_code', label='Enter the PIN Code'))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^CHQ\. (?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(ACHAT|PAIEMENT) CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(PRLV|TIP) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^VIR( SEPA)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^AVOIR (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),   FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^REM CHQ (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]


class VirtKeyboardPage(HTMLPage):
    symbols = {'0': 'gGCQotikafNwAAASxJREFUWMPtlrtKxEAUhicGJYVoYSMsRFNoYS9YipWNhWDpW/gCW1go+AqWVr6AIGi7nYWkiiBEUCxW2Q',
               '1': 'gGCQsrej4LQwAAAJRJREFUWMPt07ENAjEMhWE7do+EYANoKGhuBZZgTyp0DESBRJs4sWmYABLpTnrfANYvWyYCAPiZmU3u/o',
               '2': 'gGCQUMQbeTpgAAAlhJREFUWMPtl79rFEEUx++SE3+E+Au0NhYG/wQRUgha2YqFhZg0ghDQQgTBOoWRdEYbU0SLVRFB7JQN4g',
               '3': 'gGCQY6pSBV/AAAAh1JREFUWMPtlz2IE0EUx98bEy4fch6IMSpXiWDhB1ZqZ2FpaSmIYOF1lndWQUG46rAR7OwELTwUwTKVaJ',
               '4': 'sCBjU5C9zLzAAAAaVJREFUWMPtlzFLAzEYhpOgVKsgjoI4Skf/hZubs9V/oD9BXARB/QW1g0sXBx3EQRQEN8WhYHGSaimlQi',
               '5': 'gGCQgI83Qp8gAAAflJREFUWMPtmM9rE1EQx+fFbEhIoJQiUtCLKdKDCN71IBavPRXBs4L1D/DgyVuv/gNiD4ISrCB6KPiDtO',
               '6': 'gGCQgltqt1hwAAAqRJREFUWMPtl71rFEEYh+fUg8MYTUDwA22MQWwM2FgKKlgogpUW+gdooQkIRgs9EBu19A/wAwQLEQxKDA',
               '7': 'gGCQkLc2ZJCQAAAptJREFUWMPtlz9oFEEUxnfPRENE0ymIYCUWohYKkl4LCyFaWAi2NkFI0ErQXCE2URREFKsoKhIQ/INgLP',
               '8': 'gGCQkzW2TxlwAAAj9JREFUWMPtmD9oFEEUxuf2EA4haKOIRtHSItqKYCGCksJGEEyhWIudiO2VksZGG60uaOE1Aa8wXUwjQq',
               '9': 'gGCQobRfwKrgAAAzBJREFUWMPtl02oFEcQx8f18yASBE00qAcTgmDQQyAaPAgSCXqLAQkSJJCDYoKXQPArvPhxUhH14i05GD',}

    def get_code(self, password):
        code = ''
        for i, d in enumerate(password):
            if i > 0:
                code += '|'
            code += Attr(self.doc.xpath('//span[img[contains(@src, "%s")]]' % self.symbols[d]), 'data-matrix-key')(self)
        return code


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form()
        code = self.browser.keyboard.open().get_code(password)
        form['form[login]'] = login
        form['form[fakePassword]'] = len(password) * '•'
        form['form[password]'] = code
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    ACCOUNT_TYPES = {u'Comptes courants':      Account.TYPE_CHECKING,
                        u'Comptes épargne':       Account.TYPE_SAVINGS,
                        u'Comptes bourse':        Account.TYPE_MARKET,
                        u'Assurances Vie':        Account.TYPE_LIFE_INSURANCE,
                        u'Mes crédits':           Account.TYPE_LOAN,
                    }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@class="table table--accounts"]/tr[has-class("table__line--account") and count(descendant::td) > 1]'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad

            obj_id = Async('details') & Regexp(CleanText('//h3[has-class("account-number")]'), r'(\d+)')
            obj_label = CleanText('.//a[@class="account--name"]')
            obj_balance = CleanDecimal('.//a[has-class("account--balance")]', replace_dots=True)
            obj_currency = FrenchTransaction.Currency('.//a[has-class("account--balance")]')
            obj_valuation_diff = Async('details') & CleanDecimal('//li[h4[text()="Total des +/- values"]]/h3 |\
                        //li[span[text()="Total des +/- values latentes"]]/span[has-class("overview__value")]', replace_dots=True, default=NotAvailable)
            obj_coming = Async('details') & CleanDecimal(u'//li[h4[text()="Mouvements à venir"]]/h3', replace_dots=True, default=NotAvailable)
            obj__card = Async('details') & Attr('//a[@data-modal-behavior="credit_card-modal-trigger"]', 'href', default=NotAvailable)
            obj__holder = None

            def obj_type(self):
                return self.page.ACCOUNT_TYPES.get(CleanText('./preceding-sibling::tr[has-class("list--accounts--master")]//h4')(self), Account.TYPE_UNKNOWN)

            def obj__link(self):
                link = Attr('.//a[@class="account--name"]', 'href', default=NotAvailable)(self)
                if not self.page.browser.webid:
                    self.page.browser.webid = re.search('\/([^\/|?|$]{32})(\/|\?|$)', link).group(1)
                return '%smouvements' % link if link.startswith('/budget') else link

            # We do not yield other banks accounts for the moment.
            def condition(self):
                return not Async('details', CleanText(u'//h4[contains(text(), "Établissement bancaire")]'))(self)


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//ul[has-class("list__movement")]/li[div and not(contains(@class, "summary"))]'

        class item(ItemElement):
            klass = Transaction

            obj_id = Attr('.', 'data-id')
            obj_raw = Transaction.Raw(CleanText('.//div[@class="list__movement__line--label"]'))
            obj_date = Date(Attr('.//time', 'datetime'))
            obj_amount = CleanDecimal('.//div[contains(@class, "amount")]', replace_dots=True)
            obj_category = CleanText('.//div[contains(@class, "desc")]')


            def obj_rdate(self):
                s = Regexp(Field('raw'), ' (\d{6}) ', default=NotAvailable)(self)
                if not s:
                    return Field('date')(self)
                return Date(dayfirst=True).filter('%s%s%s%s%s' % (s[:2], '-', s[2:4], '-', s[4:]))

            def obj__is_coming(self):
                return len(self.xpath(u'.//span[@title="Mouvement à débit différé"]'))


class CardPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//select/option[not(@disabled)]'

        class item(ItemElement):
            klass = Account

            # These ids are the same card accounts had with the old website. We could get better ones without this constraint.
            obj_id = Regexp(Attr('.', 'href'), 'limite/[^/]+/([^$]+)$')
            obj_label = Regexp(CleanText('.'), '^(.*) ')
            obj__holder = Regexp(CleanText('.'), '- (.*) ')
            obj_number = Regexp(CleanText('.'), '([^ ]+)$')
            obj_type = Account.TYPE_CARD

            def condition(self):
                # We do not yield immediat debit card.
                return 'DIFFERE' in Field('label')(self)

class Myiter_investment(TableElement):
    item_xpath = '//table[contains(@class, "operations")]/tbody/tr'
    head_xpath = '//table[contains(@class, "operations")]/thead/tr/th'

    col_value = u'Valeur'
    col_quantity = u'Quantité'
    col_unitprice = u'Px. Revient'
    col_unitvalue = u'Cours'
    col_valuation = u'Montant'
    col_diff = u'+/- latentes'

class Myitem(ItemElement):
    klass = Investment

    obj_quantity = CleanDecimal(TableCell('quantity'))
    obj_unitprice = CleanDecimal(TableCell('unitprice'), replace_dots=True, default=NotAvailable)
    obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
    obj_valuation = CleanDecimal(TableCell('valuation'))
    obj_diff = CleanDecimal(TableCell('diff'), replace_dots=True)

    def obj_label(self):
        return CleanText().filter((TableCell('value')(self)[0]).xpath('.//a'))

    def obj_code(self):
        return CleanText().filter((TableCell('value')(self)[0]).xpath('./span')) or NotAvailable

class MarketPage(LoggedPage, HTMLPage):
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr'
        head_xpath = '//table/thead/tr/th'

        col_label = 'Nature'
        col_amount = 'Montant'
        col_date = 'Date d\'effet'

        class item(ItemElement):
            klass = FrenchTransaction

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True, default=NotAvailable)
            obj__is_coming = False

    @method
    class iter_investment(Myiter_investment):
        class item (Myitem):
            def obj_unitvalue(self):
                return CleanDecimal(replace_dots=True, default=NotAvailable).filter((TableCell('unitvalue')(self)[0]).xpath('./span[not(@class)]'))


class AsvPage(MarketPage):
    @method
    class iter_investment(Myiter_investment):
        col_vdate = u'Date de Valeur'

        class item(Myitem):
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)


class AccbisPage(LoggedPage, HTMLPage):
    def populate(self, accounts):
        for account in accounts:
            for li in  self.doc.xpath('//li[@class="nav-category"]'):
                title = CleanText().filter(li.xpath('./h3'))
                for a in li.xpath('./ul/li/a'):
                    label = CleanText().filter(a.xpath('./span[@class="nav-category__name"]'))
                    if account._holder and account._holder in label:
                        balance = a.xpath('./span[@class="nav-category__value"]')
                        account.balance = CleanDecimal(replace_dots=True).filter(balance)
                        account.currency = FrenchTransaction.Currency().filter(balance)
                        account._link = Link().filter(a.xpath('.'))
                        account._history_page = account._link
                        account._webid = Regexp(pattern='([^=]+)$').filter(Link().filter(a.xpath('.')))
                    elif account.label == label:
                        if not account.type:
                            account.type = AccountsPage.ACCOUNT_TYPES.get(title, Account.TYPE_UNKNOWN)
                        if account.type == Account.TYPE_LOAN:
                            account._history_page = None
                        elif account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
                            account._history_page = re.sub('/$', '', Link().filter(a.xpath('.')))
                        elif 'titulaire' in self.url:
                            account._history_page = self.browser.budget_transactions
                        else:
                            account._history_page = self.browser.other_transactions
                        account._webid = Attr(None, 'data-account-label').filter(a.xpath('./span[@class="nav-category__name"]'))

class LoanPage(LoggedPage, HTMLPage):
    pass
