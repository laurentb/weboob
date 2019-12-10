# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from datetime import datetime
from io import BytesIO

import dateutil.parser
from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import TableCell, Attr
from weboob.browser.elements import DictElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Regexp, Format, Eval, BrowserURL, Field,
    Currency,
)
from weboob.capabilities.bank import Transaction, Account, Investment
from weboob.capabilities.profile import Person
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.date import parse_french_date
from weboob.capabilities import NotAvailable
from weboob.exceptions import ActionNeeded, BrowserForbidden

def fromtimestamp(milliseconds):
    return datetime.fromtimestamp(milliseconds/1000)


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': '8adee734aaefb163fb008d26bb9b3a42',
               '1': 'dad45ef18a75200030073ab102155e2f',
               '2': '6cb4c69361f5ce32b68b477db98dd0fb',
               '3': 'aa9f2d90c8112b84805d908938eefff7',
               '4': '5aa9329aceab4318c2c96130915e87b7',
               '5': 'd9fbfdf531ad888a9d79855536905d23',
               '6': '50ce19be233ac07bebb59a16a3b9d4a7',
               '7': '3a1f932237aab949fa6c59565823218b',
               '8': 'd46cf28408db75caa915edb871ea573a',
               '9': '87686fd75d283905d7651e1098db0882',
               }

    color = (0, 0, 0)

    def __init__(self, page):
        img = page.doc.find('//img[@usemap="#gridpass_map_name"]')
        res = page.browser.open(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, BytesIO(res.content), page.doc, img, self.color, convert='RGB')
        self.check_symbols(self.symbols, None)

    def check_color(self, pixel):
        return pixel[0] < 100

    def get_symbol_coords(self, coords):
        x1, y1, x2, y2 = coords

        return MappedVirtKeyboard.get_symbol_coords(self, (x1 + 10, y1 + 10, x2 - 10, y2 - 10))

    def get_symbol_code(self, md5sum):
        m = re.search('(\d+)', MappedVirtKeyboard.get_symbol_code(self, md5sum))
        if m:
            return m.group(1)


class LoginPage(HTMLPage):
    def get_password(self, password):
        vk_passwd = None

        try:
            vk = BNPVirtKeyboard(self)
            vk_passwd = vk.get_string_code(password)
        except VirtKeyboardError as e:
            self.logger.error(e)
            raise

        return vk_passwd


class AuthPage(HTMLPage):
    def on_load(self):
        content = CleanText(u'//p[contains(text(), "Vous n\'êtes pas autorisée à afficher cette page")]')(self.doc)
        if content:
            raise BrowserForbidden(content)


class ActionNeededPage(HTMLPage):
    def on_load(self):
        raise ActionNeeded(CleanText('//p[@class="message"]')(self.doc))


class AccountsPage(LoggedPage, JsonPage):
    TYPES = {
        'Compte chèque':  Account.TYPE_CHECKING,
        'Compte à vue':   Account.TYPE_CHECKING,
    }

    @method
    class iter_accounts(DictElement):
        item_xpath = "tableauSoldes/listeGroupes/*/listeComptes"

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                return CleanText(Dict('numeroCompte'))(self)[2:]

            obj_balance = Eval(
                lambda x, y: x / 10**y,
                CleanDecimal(Dict('soldeComptable')),
                CleanDecimal(Dict('decSoldeComptable'))
            )
            obj_label = CleanText(Dict('libelleCompte'))
            obj_currency = CleanText(Dict('deviseTenue'))
            obj_iban = CleanText(Dict('numeroCompte', default=None), default=NotAvailable)

            def obj_type(self):
                return self.page.TYPES.get(Dict('libelleType')(self), Account.TYPE_UNKNOWN)

            def obj_coming(self):
                page = self.page.browser.open(
                    BrowserURL('account_coming', identifiant=Field('iban'))(self)
                ).page

                nb_decimal = 0
                if 'nb_dec' in Dict('infoOperationsAvenir/cumulTotal')(page.doc):
                    nb_decimal = Dict('infoOperationsAvenir/cumulTotal/nb_dec')
                elif 'nbDec' in Dict('infoOperationsAvenir/cumulTotal')(page.doc):
                    nb_decimal = Dict('infoOperationsAvenir/cumulTotal/nbDec')

                coming = Eval(
                    lambda x, y: x / 10**y,
                    CleanDecimal(Dict('infoOperationsAvenir/cumulTotal/montant', default='0')),
                    CleanDecimal(nb_decimal)
                )(page.doc)

                return coming


class AccountHistoryViewPage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Person

        obj_name = Regexp(CleanText('//p[@class="brandbar-info"]'), '(.+?)\s-')


class BnpHistoryItem(ItemElement):

    def obj_raw(self):
        if self.el.get('nature.libelle') and self.el.get('libelle'):
            return "%s %s" % (
                CleanText(Dict('nature/libelle'))(self),
                CleanText(Dict('libelle'))(self),
            )
        elif self.el.get('libelle'):
            return CleanText(Dict('libelle'))(self)
        else:
            return CleanText(Dict('nature/libelle'))(self)

    def obj_rdate(self):
        raw = self.obj_raw()
        mtc = re.search(r'\bDU (\d{2})\.?(\d{2})\.?(\d{2})\b', raw)
        if mtc:
            date = '%s/%s/%s' % (mtc.group(1), mtc.group(2), mtc.group(3))
            return parse_french_date(date)

        # The date can be truncated, so it is not retrieved
        if 'dateCreation' in self.el:
            return fromtimestamp(Dict('dateCreation')(self))

    @staticmethod
    def calculate_decimal(x, y):
        return x / 10 ** y


class CardItemElement(ItemElement):
    def load_details(self):
        if not Field('raw')(self).startswith('FACTURE CARTE'):
            return

        url = self.page.browser.transaction_detail.build()
        return self.page.browser.open(url, is_async=True, data={
            'type_mvt': self.detail_type_mvt,
            'numero_mvt': Field('_trid')(self),
        })


class AccountHistoryPage(LoggedPage, JsonPage):
    TYPES = {
        'CARTE': Transaction.TYPE_DEFERRED_CARD,  # Cartes
        'CHEQU': Transaction.TYPE_CHECK,  # Chèques
        'REMCB': Transaction.TYPE_DEFERRED_CARD,  # Remises cartes
        'VIREM': Transaction.TYPE_TRANSFER,  # Virements
        'VIRIT': Transaction.TYPE_TRANSFER,  # Virements internationaux
        'VIRSP': Transaction.TYPE_TRANSFER,  # Virements européens
        'VIRTR': Transaction.TYPE_TRANSFER,  # Virements de trésorerie
        'VIRXX': Transaction.TYPE_TRANSFER,  # Autres virements
        'PRLVT': Transaction.TYPE_ORDER,  # Prélèvements, TIP et télérèglements
        'AUTOP': Transaction.TYPE_UNKNOWN,  # Autres opérations

        'FACCB': Transaction.TYPE_CARD,   # Cartes
    }

    COMING_TYPES = {
        '0001': Transaction.TYPE_CHECK,  # CHEQUE
        '0029': Transaction.TYPE_BANK,  # Interets et Commissions
        '0083': Transaction.TYPE_DEFERRED_CARD,
        '0099': Transaction.TYPE_PAYBACK,  # REM. CARTE OU EROCHQ.*
        '0512': Transaction.TYPE_TRANSFER,  # VIREMENT FAVEUR TIERS
        '0558': Transaction.TYPE_TRANSFER,  # VIREMENT RECU TIERS.*
        '0568': Transaction.TYPE_TRANSFER,  # VIREMENT SEPA
        '0813': Transaction.TYPE_ORDER,  # PRLV SEPA .*
        '1194': Transaction.TYPE_DEFERRED_CARD,  # PAYBACK typed as DEFERRED_CARD
    }

    @method
    class iter_history(DictElement):
        item_xpath = "mouvementsBDDF"

        class item(CardItemElement):
            klass = Transaction

            obj_original_currency = CleanText(Dict('montant/devise'))
            obj__coming = Dict('avenir')

            @property
            def detail_type_mvt(self):
                if Field('_coming')(self):
                    return 2
                return 1

            def obj_raw(self):
                nature = CleanText(Dict('nature/libelle'))(self)
                label = CleanText(Dict('libelle'))(self)
                if nature and label:
                    return "%s %s" % (nature, label)
                elif label:
                    return label
                else:
                    return nature

            def obj_type(self):
                type = self.page.TYPES.get(Dict('nature/codefamille')(self), Transaction.TYPE_UNKNOWN)
                if (
                    (type == Transaction.TYPE_CARD and re.search(r' RELEVE DU \d+\.', Field('raw')(self))) or
                    (type == Transaction.TYPE_UNKNOWN and re.search(r'FACTURE CARTE AFFAIRES \w{16} SUIVANT RELEVE DU \d{2}.\d{2}.\d{4}', Field('raw')(self)))
                ):
                    return Transaction.TYPE_CARD_SUMMARY
                return type

            def obj_date(self):
                return fromtimestamp(Dict('dateOperation')(self))

            def obj_rdate(self):
                raw = self.obj_raw()
                mtc = re.search(r'\bDU (\d{6}|\d{8})\b', raw)

                if mtc:
                    numbers = mtc.group(1)
                    # we need to create this string because dateutil crashes
                    # with dates in the ddmmyyyy format
                    # dd/mm/yy and dd/mm/yyyy
                    date = '%s/%s/%s' % (numbers[0:2], numbers[2:4], numbers[4:])
                    try:
                        return dateutil.parser.parse(date, dayfirst=True)
                    except ValueError:
                        # parsing failed assuming yyyymmdd format
                        return dateutil.parser.parse(numbers)

                return fromtimestamp(Dict('dateCreation')(self))

            def obj_vdate(self):
                return fromtimestamp(Dict('dateValeur')(self))

            def obj_amount(self):
                decimal_nb = Dict('montant/nbDec', default=None)(self)\
                                or Dict('montant/nb_dec')(self)

                return Eval(
                    lambda x, y: x / 10**y,
                    CleanDecimal(Dict('montant/montant')),
                    decimal_nb
                )(self)

            obj__trid = Dict('id')

    @method
    class iter_coming(DictElement):
        item_xpath = "infoOperationsAvenir/operationsAvenir"

        class item(CardItemElement):
            klass = Transaction

            detail_type_mvt = 2

            obj__coming = True

            obj_date = Date(Dict('dateOpeMvmt'))
            obj_rdate = Date(Dict('dateCreatMvmt'))
            obj_vdate = Date(Dict('dateValMvmt'))
            obj_original_currency = CleanText(Dict('montantMvmt/devise'))

            def obj_raw(self):
                if not Dict('natureLibelleMvt')(self):
                    return CleanText(Dict('libelle'))(self)
                return Format('%s %s', CleanText(Dict('natureLibelleMvt')), CleanText(Dict('libelle')))(self)

            def obj_type(self):
                return self.page.COMING_TYPES.get(Dict('codeMouvement')(self), Transaction.TYPE_UNKNOWN)

            def obj_amount(self):
                decimal_nb = Dict('montantMvmt/nbDec', default=None)(self)\
                                or Dict('montantMvmt/nb_dec')(self)

                return Eval(
                    lambda x, y: x / 10**y,
                    CleanDecimal(Dict('montantMvmt/montant')),
                    decimal_nb
                )(self)

            obj__trid = Dict('idMouvement')


class TransactionPage(LoggedPage, JsonPage):
    pass


class MarketPage(LoggedPage, HTMLPage):
    TYPES = {
        'comptes de titres':  Account.TYPE_MARKET,
    }

    @method
    class iter_market_accounts(TableElement):
        def condition(self):
            return not self.el.xpath('//table[@id="table-portefeuille"]//tr/td[contains(text(), "Aucun portefeuille à afficher") \
                or contains(text(), "No portfolio to display")]')

        item_xpath = '//table[@id="table-portefeuille"]/tbody[@class="main-content"]/tr'
        head_xpath = '//table[@id="table-portefeuille"]/thead/tr/th/label'

        col_label = 'Portefeuille-titres'
        col_balance = re.compile('Valorisation')
        col__parent = re.compile('Compte courant')

        class item(ItemElement):
            klass = Account

            # Market accounts have no IBAN so we use the account number and specify
            # "MARKET" at the end to differentiate from its parent account.
            obj_id = Format('%sMARKET', Regexp(CleanText(TableCell('label')), r'\*(.*)\*', default=None))
            obj_label = CleanText(TableCell('label'))
            obj_balance = CleanDecimal(TableCell('balance'), replace_dots=True)
            obj_currency = Currency(TableCell('balance'))
            obj__parent = CleanText(TableCell('_parent'))
            obj_coming = NotAvailable
            obj_iban = NotAvailable
            obj__unique = False

            def obj_type(self):
                for key, type in self.page.TYPES.items():
                    if key in CleanText(TableCell('label'))(self).lower():
                        return type
                return Account.TYPE_UNKNOWN

    def get_token(self):
        return Attr('//meta[@name="_csrf"]', 'content')(self.doc)

    def get_id(self, label):
        id_simple = re.search(r'[0-9]+', label).group(0)
        for options in self.doc.xpath('//div[@class="filterbox-content hide"]//select[@id="numero-compte-titre"]//option'):
            if id_simple in CleanText(options)(self.doc):
                return CleanText(options.xpath('./@value'))(self)


class InvestPage(LoggedPage, HTMLPage):
    @method
    class get_unique_market_account(ItemElement):
        klass = Account

        # Market accounts have no IBAN so we use the account number and specify
        # "MARKET" at the end to differentiate it from its parent account.
        obj_id = Format('%sMARKET', Regexp(CleanText('//div[@class="head"]/h2'), r'\*(.*)\*', default=None))
        obj_label = CleanText('//div[@class="head"]/h2')
        obj_balance = CleanDecimal('//div[@id="apercu-val"]/h1', replace_dots=True)
        obj_currency = Currency('//div[@id="apercu-val"]/h1')
        obj_type = Account.TYPE_MARKET
        obj__parent = CleanText('//h3/span[span[@class="info-cheque"]]', children=False)
        obj__unique = True


    @method
    class iter_investment(TableElement):
        item_xpath = '//table[@class="csv-data-container hide"]//tr'
        head_xpath = '//table[@class="csv-data-container hide"]//th'

        col_quantity = 'Nombre de parts'
        col_label = 'Fonds'
        col_unitprice = 'PAMP'
        col_unitvalue = 'Valeur de la part'
        col_valuation = 'Valorisation'
        col_diff = '+/- value'

        """
        Note: Pagination is not handled yet for investments, if we find a
        customer with more than 10 invests we might have to handle clicking
        on the button to get 50 invests per page or check if there is a link.
        """

        class item(ItemElement):
            klass = Investment

            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)
            obj_label = CleanText(TableCell('label'))
            obj_unitprice = CleanDecimal(TableCell('unitprice'), replace_dots=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_diff = CleanDecimal(TableCell('diff'), replace_dots=True)
            obj_code_type = lambda self: Investment.CODE_TYPE_ISIN if Field('code')(self) is not NotAvailable else NotAvailable

            def obj_code(self):
                string = CleanText(TableCell('label'))(self)
                return re.search(r'(\w+) - ', string).group(0)[:-3]
