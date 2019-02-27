# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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
import base64
from io import BytesIO
from PIL import Image

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.standard import (
    Regexp, Field, CleanText, CleanDecimal, Eval, Currency
)
from weboob.browser.filters.html import Link, TableCell, Attr, AttributeNotFound
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class CarrefourBanqueKeyboard(object):
    symbols = {
        '0': '00111001111110111011011001111100011110001111000111100111110011111111100111100',
        '1': '00011000011100011110011011000001100000110000011000001100000110000011000001100',
        '2': '00111001111110110011100001110000110000111000111000011000011000011111111111111',
        '3': '01111001111110100011100001110001110011110000111100000111000011111111111111110',
        '4': '00001100001110001111000111100110110110011011001101111111111111100001100000110',
        '5': '01111101111110111000011000001111100111111000001110000111000011111111101111100',
        '6': '00011100111110111000011000001111110111111111001111100011110001111111110111110',
        '7': '11111111111111000011100001100000110000110000011000011100001100001110000110000',
        '8': '00111001111110110011111001111111110011110011111101100111110001111111110111110',
        '9': '00110001111110110011111000111100011111111111111110000011000011011111101111100'
    }

    def __init__(self, data_code):
        self.fingerprints = {}

        for code, data in data_code.items():
            img = Image.open(BytesIO(data))
            img = img.convert('RGB')
            matrix = img.load()
            s = ""
            # The digit is only displayed in the center of image
            for y in range(11, 22):
                for x in range(14, 21):
                    (r, g, b) = matrix[x, y]
                    # If the pixel is "white" enough
                    if r + g + b > 600:
                        s += "1"
                    else:
                        s += "0"

            self.fingerprints[code] = s

    def get_symbol_code(self, digit):
        fingerprint = self.symbols[digit]
        for code, string in self.fingerprints.items():
            if string == fingerprint:
                return code
        # Image contains some noise, and the match is not always perfect
        # (this is why we can't use md5 hashs)
        # But if we can't find the perfect one, we can take the best one
        best = 0
        result = None
        for code, string in self.fingerprints.items():
            match = 0
            for j, bit in enumerate(string):
                if bit == fingerprint[j]:
                    match += 1
            if match > best:
                best = match
                result = code
        return result

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(c) + '-'
        return code


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def on_load(self):
        """
        website may have identify us as a robot, if it happens login form won't be available in login page
        and there will be nothing on body except a meta tag with robot name
        """
        try:
            attr = Attr('head/meta', 'name')(self.doc)
        except AttributeNotFound:
            # website have identify us as a human ;)
            return

        # sometimes robots is uppercase and there is an iframe
        # sometimes it's lowercase and there is a script
        if attr == 'ROBOTS':
            self.browser.location(Attr('//iframe', 'src')(self.doc))
        elif attr == 'robots':
            self.browser.location(Attr('//script', 'src')(self.doc))

    def enter_login(self, username):
        form = self.get_form(nr=1)
        form['name'] = username
        form.submit()

    def get_message_if_old_login(self):
        return CleanText('//div[@class="messages error"]', children=False)(self.doc)

    def enter_password(self, password):
        data_code = {}
        for img in self.doc.xpath('//img[@class="digit"]'):
            data_code[img.attrib['data-code']] = base64.b64decode(re.search(r'base64,(.*)', img.attrib['src']).group(1))

        codestring = CarrefourBanqueKeyboard(data_code).get_string_code(password)

        form = self.get_form(nr=1)
        form['pass'] = '*' * len(password)
        form['cpass'] = codestring
        form.pop('form_number') # don't remember me

        form.submit()


class MaintenancePage(HTMLPage):
    def get_message(self):
        return CleanText('//div[@class="bloc-title"]/h1//div[has-class("field-item")]')(self.doc)


class IncapsulaResourcePage(HTMLPage):
    def __init__(self, *args, **kwargs):
        # this page can be a html page, or just javascript
        super(IncapsulaResourcePage, self).__init__(*args, **kwargs)
        self.is_javascript = None

    def on_load(self):
        self.is_javascript = 'html' not in CleanText('*')(self.doc)

    def get_recaptcha_site_key(self):
        return Attr('//div[@class="g-recaptcha"]', 'data-sitekey')(self.doc)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>.*?) (?P<dd>\d{2})/(?P<mm>\d{2})$'), FrenchTransaction.TYPE_CARD)]


class item_account_generic(ItemElement):
    """Generic accounts properties for Carrefour homepage"""
    klass = Account

    def obj_balance(self):
        balance = CleanDecimal('.//div[contains(@class, "right_col")]//h2[1]', replace_dots=True)(self)
        return (-balance if Field('type')(self) in (Account.TYPE_LOAN,) else balance)

    obj_currency = Currency('.//div[contains(@class, "right_col")]//h2[1]')
    obj_label = CleanText('.//div[contains(@class, "leftcol")]//h2[1]')
    obj_id = Regexp(CleanText('.//div[contains(@class, "leftcol")]//p'), ":\s+([\d]+)")
    obj_number = Field('id')

    def obj_url(self):
        acc_number = Field('id')(self)
        xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a'.format(acc_number=acc_number)
        return Link(xpath_link)(self)


class iter_history_generic(Transaction.TransactionsElement):
    head_xpath = u'//div[*[contains(text(), "opérations")]]/table//thead/tr/th'
    item_xpath = u'//div[*[contains(text(), "opérations")]]/table/tbody/tr[td]'

    col_debittype = 'Mode'

    def next_page(self):
        next_page = Link(u'//a[contains(text(), "précédentes")]', default=None)(self)
        if next_page:
            return "/%s" % next_page

    class item(Transaction.TransactionElement):
        def obj_type(self):
            if len(self.el.xpath('./td')) <= 3:
                return Transaction.TYPE_BANK

            debittype = CleanText(TableCell('debittype'))(self)
            if debittype == 'Différé':
                return Transaction.TYPE_DEFERRED_CARD
            return Transaction.TYPE_CARD

        def condition(self):
            return TableCell('raw')(self)


class HomePage(LoggedPage, HTMLPage):
    @method
    class iter_loan_accounts(ListElement):  # Prêts
        item_xpath = '//div[@class="pp_espace_client"]'

        class item(item_account_generic):
            obj_type = Account.TYPE_LOAN

    @method
    class iter_card_accounts(ListElement):  # PASS cards
        item_xpath = '//div/div[contains(./h2, "Carte et Crédit") and contains(./p, "Numéro de compte")]/..'

        class item(item_account_generic):
            obj_type = Account.TYPE_CARD

            def obj_balance(self):
                available = CleanDecimal('.//p[contains(., "encours depuis le")]//preceding-sibling::h2', default=None, replace_dots=True)(self)
                return NotAvailable if not available else -available

    @method
    class iter_saving_accounts(ListElement):  # livrets
        item_xpath = (
            '//div[div[(contains(./h2, "Livret Carrefour") or contains(./h2, "Epargne")) and contains(./p, "Numéro de compte")]]'
        )

        class item(item_account_generic):
            obj_type = Account.TYPE_SAVINGS
            obj_url = Link('.//a[contains(., "Historique des opérations")]')

            def obj_balance(self):
                val = CleanDecimal('.//a[contains(text(), "versement")]//preceding-sibling::h2', replace_dots=True, default=NotAvailable)(self)
                if val is not NotAvailable:
                    return val
                val = CleanDecimal(Regexp(CleanText('./div[@class="right_col_wrapper"]//h2'), r'([\d ,]+€)'), replace_dots=True)(self)
                return val

    @method
    class iter_life_accounts(ListElement):  # Assurances vie
        item_xpath = '//div/div[(contains(./h2, "Carrefour Horizons") or contains(./h2, "Carrefour Avenir")) and contains(./p, "Numéro de compte")]/..'

        class item(item_account_generic):
            obj_type = Account.TYPE_LIFE_INSURANCE

            def obj_url(self):
                acc_number = Field('id')(self)
                xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a[contains(text(), "Dernieres opérations")]'.format(acc_number=acc_number)
                return Link(xpath_link)(self)

            def obj__life_investments(self):
                xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a[contains(text(), "Solde")]'.format(acc_number=Field('id')(self))
                return Link(xpath_link)(self)


class TransactionsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(iter_history_generic):
        pass


class SavingHistoryPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(iter_history_generic):
        head_xpath = '//table[@id="creditHistory" or @id="TransactionHistory"]/thead/tr/th'
        item_xpath = '//table[@id="creditHistory" or @id="TransactionHistory"]/tbody/tr'


class LifeInvestmentsPage(LoggedPage, HTMLPage):
    @method
    class get_investment(TableElement):
        item_xpath = '//table[@id="assets"]/tbody/tr[position() > 1]'
        head_xpath = '//table[@id="assets"]/tbody/tr[1]/td'

        col_label = u'Fonds'
        col_quantity = u'Nombre de parts'
        col_unitvalue = u'Valeur part'
        col_valuation = u'Total'
        col_portfolio_share = u'Répartition'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_portfolio_share = Eval(lambda x: x / 100, MyDecimal(TableCell('portfolio_share')))


class LifeHistoryPage(TransactionsPage):
    pass


class LoanHistoryPage(TransactionsPage):
    pass


class CardHistoryPage(TransactionsPage):
    pass
