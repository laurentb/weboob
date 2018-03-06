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

from decimal import Decimal

from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage
from weboob.browser.filters.json import Dict
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Regexp, Format, Eval, BrowserURL, Field, Env,
    Async,
)
from weboob.capabilities.bank import Transaction, Account
from weboob.capabilities.profile import Person
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError
from weboob.tools.date import parse_french_date
from weboob.capabilities import NotAvailable
from weboob.exceptions import ActionNeeded, BrowserForbidden


def merge_cards(input_list):
    final_card_set = {}

    # step 1: merge cards
    for card in input_list:
        card_number = card.number
        if card_number in final_card_set:
            if card._coming_amount:
                final_card_set[card_number] = card
        else:
            final_card_set[card_number] = card

    # step 2: update card.id
    output = []
    for card in final_card_set.values():
        card.id, _index = card.id.rsplit('.', 1)
        assert card._index == _index
        output.append(card)

    return output

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
    TYPES = {u'Compte chèque': Account.TYPE_CHECKING}

    @method
    class iter_accounts(DictElement):
        item_xpath = "tableauSoldes/listeGroupes/*/listeComptes"

        class item(ItemElement):
            klass = Account

            obj__has_cards = Dict('encoursCB')

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
                coming = Eval(
                    lambda x, y: x / 10**y,
                    CleanDecimal(Dict('infoOperationsAvenir/cumulTotal/montant', default='0')),
                    CleanDecimal(Dict('infoOperationsAvenir/cumulTotal/nb_dec', default='0'))
                )(page.doc)

                # this so that card coming transactions aren't accounted twice in the total incoming amount
                for el in Dict('infoOperationsAvenir/natures')(page.doc):
                    if Dict('nature/libelle')(el) == "Factures / Retraits cartes":
                        coming_carte = Eval(
                            lambda x, y: x / 10**y,
                            CleanDecimal(Dict('cumulNatureMere/montant', default='0')),
                            CleanDecimal(Dict('cumulNatureMere/nb_dec', default='0'))
                        )(el)
                        coming -= coming_carte
                        break

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

        return fromtimestamp(Dict('dateCreation')(self))

    @staticmethod
    def calculate_decimal(x, y):
        return x / 10 ** y


class CardItemElement(ItemElement):
    def load_details(self):
        # to avoid loading coming details
        if Field('_coming')(self):
            return

        if not Field('raw')(self).startswith('FACTURE CARTE'):
            return

        url = self.page.browser.transaction_detail.build()
        return self.page.browser.open(url, is_async=True, data={
            'type_mvt': self.detail_type_mvt,
            'numero_mvt': Field('_trid')(self),
        })

    def obj__redacted_card(self):
        raw = Field('raw')(self)
        # loading coming details is not necessary here
        if Field('_coming')(self):
            return

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

            detail_type_mvt = 1

            obj_original_currency = CleanText(Dict('montant/devise'))
            obj__coming = Dict('avenir')

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
                mtc = re.search(r'\bDU (\d{8})\b', raw)
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


class CardListPage(LoggedPage, JsonPage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'listEncourCartes'

        class item(ItemElement):
            klass = Account

            obj_type = Account.TYPE_CARD
            obj_number = Dict('numCarte')
            obj__redacted_card = Dict('formatedNumCarte')
            obj_id = Format('%s.%s.%s', Env('account_id'), Dict('numCarte'), Dict('idCarte'))
            obj_label = Format('%s %s', Dict('typeCarte'), Dict('nomPorteur'))
            obj__index = Dict('idCarte')
            obj__coming_amount = Dict('montantLigneEncours')
            obj__parent_iban = Env('parent_iban')
            obj_coming = Eval(lambda x: Decimal(x)/100, Dict('montant/montant'))
            obj_currency = CleanText(Dict('montant/devise'))


class CardHistoryPage(LoggedPage, JsonPage):
    @method
    class iter_coming(DictElement):
        item_xpath = 'listOperationCarteDataBean'

        class item(BnpHistoryItem):
            klass = Transaction

            obj_type = Transaction.TYPE_DEFERRED_CARD
            obj_date = obj_vdate = Date(Dict('valeur'), dayfirst=True)

            def obj_amount(self):
                amount = Dict('debit', default=None)(self) or Dict('credit')(self)
                decimal_nb = Dict('nbDec', default=None)(amount)\
                                or Dict('nb_dec')(amount)

                return Eval(
                    lambda x, y: x / 10**y,
                    Decimal(amount['montant']),
                    decimal_nb
                )(self)


class TransactionPage(LoggedPage, JsonPage):
    def get_redacted_card(self):
        # warning: the account on which the transaction is returned depends on this data!
        return self.doc['carteNum']
