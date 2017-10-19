# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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

from datetime import datetime

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, Date, Field, CleanText, Env
from weboob.browser.filters.json import Dict
from weboob.browser.pages import LoggedPage, JsonPage
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import NoAccountsException


class LoginPage(JsonPage):
    def get_token(self):
        return Dict('token')(self.doc)


class AccountsPage(LoggedPage, JsonPage):
    ACCOUNT_TYPES = {'PEE': Account.TYPE_PEE,
                     'PEG': Account.TYPE_PEE,
                     'PERCO': Account.TYPE_PERCO,
                     'RSP': Account.TYPE_RSP
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
            obj_number = Field('id')
            obj_currency = u"EUR"

            def obj_type(self):
                return self.page.ACCOUNT_TYPES.get(Dict('typeDispositif')(self), Account.TYPE_LIFE_INSURANCE)

            def obj_label(self):
                try:
                    return Dict('libelleDispositif')(self).encode('iso-8859-2').decode('utf8')
                except (UnicodeEncodeError, UnicodeDecodeError):
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
            obj_diff = Dict('mtPMV') & CleanDecimal


class AccountHistoryPage(LoggedPage, JsonPage):
    def belongs(self, instructions, account):
        for ins in instructions:
            if 'nomDispositif' in ins and 'codeDispositif' in ins and '%s%s' % (ins['nomDispositif'], ins['codeDispositif']) == \
               '%s%s' % (account.label, account.id):
                return True
        return False

    def get_amount(self, instructions, account):
        amount = 0

        for ins in instructions:
            if 'nomDispositif' in ins and 'montantNet' in ins and 'codeDispositif' in ins and '%s%s' % (ins['nomDispositif'], ins['codeDispositif']) == \
               '%s%s' % (account.label, account.id):
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
                    tr.label = hist['libelleOperation'] if 'libelleOperation' in hist else hist['libelleCommunication']
                    tr.type = Transaction.TYPE_UNKNOWN

                    # Bypassed because we don't have the ISIN code
                    # tr.investments = []
                    # for ins in hist['instructions']:
                    #     inv = Investment()
                    #     inv.code = NotAvailable
                    #     inv.label = ins['nomFonds']
                    #     inv.description = ' '.join([ins['type'], ins['nomDispositif']])
                    #     inv.vdate = datetime.strptime(ins.get('dateVlReel', ins.get('dateVlExecution')).split('T')[
                    # 0], '%Y-%m-%d')
                    #     inv.valuation = Decimal(ins['montantNet'])
                    #     inv.quantity = Decimal(ins['nombreDeParts'])
                    #     inv.unitprice = inv.unitvalue = Decimal(ins['vlReel'])
                    #     tr.investments.append(inv)

                    yield tr
