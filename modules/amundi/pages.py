# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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

from datetime import datetime

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanDecimal, Date, Field, CleanText, Env, Eval,
)
from weboob.browser.filters.json import Dict
from weboob.browser.pages import LoggedPage, JsonPage
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable, empty
from weboob.exceptions import NoAccountsException
from weboob.tools.capabilities.bank.investments import is_isin_valid


class LoginPage(JsonPage):
    def get_token(self):
        return Dict('token')(self.doc)


class AccountsPage(LoggedPage, JsonPage):
    def get_company_name(self):
        json_list = Dict('listPositionsSalarieFondsDto')(self.doc)
        if json_list:
            return json_list[0].get('nomEntreprise', NotAvailable)
        return NotAvailable

    ACCOUNT_TYPES = {
        'PEE': Account.TYPE_PEE,
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

            def condition(self):
                # Some additional invests are present in the JSON but are not
                # displayed on the website, besides they have no valuation,
                # so we check the 'valuation' key before parsing them
                return Dict('mtBrut', default=None)(self)

            obj_label = Dict('libelleFonds')
            obj_unitvalue = Dict('vl') & CleanDecimal
            obj_quantity = Dict('nbParts') & CleanDecimal
            obj_valuation = Dict('mtBrut') & CleanDecimal
            obj_vdate = Date(Dict('dtVl'))

            def obj_srri(self):
                srri = Dict('SRRI')(self)
                # The website displays '0 - Non disponible' when not available
                if srri.startswith('0'):
                    return NotAvailable
                return int(srri)

            def obj_code(self):
                code = Dict('codeIsin', default=NotAvailable)(self)
                if is_isin_valid(code):
                    return code
                return NotAvailable

            def obj_code_type(self):
                if empty(Field('code')(self)):
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN

            def obj_performance_history(self):
                # The Amundi JSON only contains 1 year and 5 years performances.
                # It seems that when a value is unavailable, they display '0.0' instead...
                perfs = {}
                if Dict('performanceUnAn', default=None)(self) not in (0.0, None):
                    perfs[1] = Eval(lambda x: x/100, CleanDecimal(Dict('performanceUnAn')))(self)
                if Dict('performanceCinqAns', default=None)(self) not in (0.0, None):
                    perfs[5] = Eval(lambda x: x/100, CleanDecimal(Dict('performanceCinqAns')))(self)
                return perfs


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
                if ins['type'] == 'RACH_TIT':
                    amount -= ins['montantNet']
                else:
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
