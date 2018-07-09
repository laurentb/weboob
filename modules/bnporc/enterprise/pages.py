# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from datetime import datetime
from io import BytesIO

from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import TableCell, Attr
from weboob.browser.elements import DictElement, ItemElement, method, TableElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Regexp, Format, Eval, BrowserURL, Field,
    Async,
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
    TYPES = {u'Compte chèque': Account.TYPE_CHECKING,
             u'Compte à vue': Account.TYPE_CHECKING}

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

    def obj__redacted_card(self):
        raw = Field('raw')(self)

        if not raw.startswith('FACTURE CARTE') or ' SUIVANT RELEVE DU ' in raw:
            return

        page = Async('details').loaded_page(self)
        return page.get_redacted_card()


class AccountHistoryPage(LoggedPage, JsonPage):
    TYPES = {
        u'CARTE': Transaction.TYPE_DEFERRED_CARD,  # Cartes
        u'CHEQU': Transaction.TYPE_CHECK,  # Chèques
        u'REMCB': Transaction.TYPE_DEFERRED_CARD,  # Remises cartes
        u'VIREM': Transaction.TYPE_TRANSFER,  # Virements
        u'VIRIT': Transaction.TYPE_TRANSFER,  # Virements internationaux
        u'VIRSP': Transaction.TYPE_TRANSFER,  # Virements européens
        u'VIRTR': Transaction.TYPE_TRANSFER,  # Virements de trésorerie
        u'VIRXX': Transaction.TYPE_TRANSFER,  # Autres virements
        u'PRLVT': Transaction.TYPE_LOAN_PAYMENT,  # Prélèvements, TIP et télérèglements
        u'AUTOP': Transaction.TYPE_UNKNOWN,  # Autres opérations

        'FACCB': Transaction.TYPE_CARD,   # Cartes
    }

    COMING_TYPES = {
        u'0083': Transaction.TYPE_DEFERRED_CARD,
        u'0813': Transaction.TYPE_LOAN_PAYMENT,
        u'0568': Transaction.TYPE_TRANSFER,
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
                if type == Transaction.TYPE_CARD and re.search(r' RELEVE DU \d+\.', Field('raw')(self)):
                    return Transaction.TYPE_CARD_SUMMARY
                return type

            def obj_date(self):
                return fromtimestamp(Dict('dateOperation')(self))

            def obj_rdate(self):
                raw = self.obj_raw()
                mtc = re.search(r'\bDU (\d{6}|\d{8})\b', raw)
                if mtc:
                    date = mtc.group(1)
                    date = '%s/%s/%s' % (date[0:2], date[2:4], date[4:])
                    return parse_french_date(date)

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
    def get_redacted_card(self):
        # warning: the account on which the transaction is returned depends on this data!
        return self.doc['carteNum']


class TokenPage(LoggedPage, HTMLPage):
    def get_token(self):
        return Attr('//meta[@name="_csrf"]', 'content')(self.doc)

    def get_id(self, label):
        id_simple = re.search(r'[0-9]+', label).group(0)
        for options in self.doc.xpath('//div[@class="filterbox-content hide"]//select[@id="numero-compte-titre"]//option'):
            if id_simple in CleanText(options)(self.doc):
                return CleanText(options.xpath('./@value'))(self)

    def market_search(self):
        marketaccount = []
        for account in self.doc.xpath('//div[@class="filterbox-content hide"]//select[@id="numero-compte-titre"]//option'):
            account = CleanText(account)(self.doc)
            temp = re.search(r'[0-9]+', account)
            if temp != None:
                marketaccount.append(temp.group(0))

        return marketaccount


class InvestPage(LoggedPage, HTMLPage):
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
                chaine = CleanText(TableCell('label'))(self)
                return re.search(r'(\w+) - ', chaine).group(0)[:-3]

    def get_market_account_label(self):
        return CleanText('//h3/span[span]', children=False)(self.doc)
