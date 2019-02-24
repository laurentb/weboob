# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import datetime

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, Date, Field, CleanText, Env
from weboob.browser.filters.json import Dict
from weboob.browser.pages import LoggedPage, JsonPage
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import NoAccountsException
from weboob.tools.capabilities.bank.investments import is_isin_valid


class LoginPage(JsonPage):
    def get_token(self):
        return Dict('token')(self.doc)


class AccountsPage(LoggedPage, JsonPage):
    ACCOUNT_TYPES = {'PEE': Account.TYPE_PEE,
                     'PEG': Account.TYPE_PEE,
                     'PEI': Account.TYPE_PEE,
                     'PERCO': Account.TYPE_PERCO,
                     'RSP': Account.TYPE_RSP,
                    }

    @method
    class iter_accounts(DictElement):
        def parse(self, el):
            if not el.get('count', 42):
                raise NoAccountsException()

        item_xpath = "listPositionsSalarieFondsDto/*/positionsSalarieDispositifDto"

        class item(ItemElement):
            klass = Account

            obj_id = CleanText(Dict('codeDispositif'))
            obj_balance = CleanDecimal(Dict('mtBrut'))

            def obj_number(self):
                # just the id is a kind of company id so it can be unique on a backend but not unique on multiple backends
                return '%s_%s' % (Field('id')(self), self.page.browser.username)

            obj_currency = 'EUR'

            def obj_type(self):
                return self.page.ACCOUNT_TYPES.get(Dict('typeDispositif')(self), Account.TYPE_LIFE_INSURANCE)

            def obj_label(self):
                try:
                    return Dict('libelleDispositif')(self).encode('iso-8859-2').decode('utf8')
                except UnicodeError:
                    try:
                        return Dict('libelleDispositif')(self).encode('latin1').decode('utf8')
                    except UnicodeDecodeError:
                        return Dict('libelleDispositif')(self)

    @method
    class iter_investments(DictElement):
        def find_elements(self):
            for psds in Dict('listPositionsSalarieFondsDto')(self):
                for psd in psds.get('positionsSalarieDispositifDto'):
                    if psd.get('codeDispositif') == Env('account_id')(self):
                        return psd.get('positionsSalarieFondsDto')
            return {}

        class item(ItemElement):
            klass = Investment

            obj_label = Dict('libelleFonds')
            obj_unitvalue = Dict('vl') & CleanDecimal
            obj_quantity = Dict('nbParts') & CleanDecimal
            obj_valuation = Dict('mtBrut') & CleanDecimal
            obj_code = Dict('codeIsin', default=NotAvailable)
            obj_vdate = Date(Dict('dtVl'))

            def obj_code_type(self):
                if is_isin_valid(Field('code')(self)):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable


class AccountHistoryPage(LoggedPage, JsonPage):
    def belongs(self, instructions, account):
        for ins in instructions:
            if 'nomDispositif' in ins and 'codeDispositif' in ins and '%s%s' % (
                ins['nomDispositif'], ins['codeDispositif']) == '%s%s' % (account.label, account.id):
                return True
        return False

    def get_amount(self, instructions, account):
        amount = 0

        for ins in instructions:
            if ('nomDispositif' in ins and 'montantNet' in ins and 'codeDispositif' in ins
                and '%s%s' % (ins['nomDispositif'], ins['codeDispositif'])
                    == '%s%s' % (account.label, account.id)):
                amount += ins['montantNet']

        return CleanDecimal().filter(amount)

    def iter_history(self, account):
        for hist in self.doc['operationsIndividuelles']:
            if len(hist['instructions']) > 0:
                if self.belongs(hist['instructions'], account):
                    tr = Transaction()
                    tr.amount = self.get_amount(hist['instructions'], account)
                    tr.rdate = datetime.strptime(hist['dateComptabilisation'].split('T')[0], '%Y-%m-%d')
                    tr.date = tr.rdate
                    tr.label = hist.get('libelleOperation') or hist['libelleCommunication']
                    tr.type = Transaction.TYPE_UNKNOWN

                    yield tr
