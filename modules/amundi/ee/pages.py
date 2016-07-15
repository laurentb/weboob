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
from decimal import Decimal

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.browser.filters.json import Dict
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage, pagination
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import NextPage


class FakePage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        data = {'mail': login, 'password': passwd, 'connection': ''}

        self.browser.location('/part/home_priv_synth',
                              data=data,
                              headers={'Referer': 'https://www.amundi-ee.com/part/home_login'})

    def is_here(self):
        return bool(self.doc.xpath('//a[@href="home_login"]'))


class AccountsPage(LoggedPage, JsonPage):
    def iter_accounts(self):
        types = {'PEE': Account.TYPE_PEE, 'PEG': Account.TYPE_PEE,
                 'PERCO': Account.TYPE_PERCO, 'RSP': Account.TYPE_RSP}
        for acc in self.doc['positionTotaleDispositifDto']:
            ac = Account()
            ac.type = types.get(acc['typeDispositif'], Account.TYPE_LIFE_INSURANCE)
            ac.id = ac.number = acc['codeDispositif']
            try:
                ac.label = acc['libelleDispositif'].encode('latin1').decode('utf8')
            except UnicodeDecodeError:
                ac.label = acc['libelleDispositif']
            ac._entreprise = acc['libelleEntreprise']
            ac.balance = Decimal(acc['mtBrut'])
            ac._ident = acc['idEnt']
            yield ac


class AccountDetailPage(LoggedPage, JsonPage):
    def is_here(self):
        return 'positionsSalarieDispositifDto' in self.doc

    @method
    class iter_investments(DictElement):
        def find_elements(self):
            for dispositif in self.page.doc['positionsSalarieDispositifDto']:
                if self.env['account_id'] == dispositif['codeDispositif']:
                    return dispositif['positionsSalarieFondsDto']
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
    def belongs(self, instructions, data):
        for ins in instructions:
            if 'nomDispositif' in ins and 'codeDispositif' in ins and '%s%s' % (ins['nomDispositif'], ins['codeDispositif']) == \
               '%s%s' % (data['acc'].label, data['acc'].id):
                return True
        return False

    def get_amount(self, instructions, data):
        amount = 0
        for ins in instructions:
            if 'nomDispositif' in ins and 'montantNet' in ins and 'codeDispositif' in ins and '%s%s' % (ins['nomDispositif'], ins['codeDispositif']) == \
               '%s%s' % (data['acc'].label, data['acc'].id):
                amount += ins['montantNet']
        return Decimal(amount)

    @pagination
    def iter_history(self, data):
        for hist in self.doc['operationsIndividuelles']:
            if len(hist['instructions']) > 0:
                if self.belongs(hist['instructions'], data):
                    tr = Transaction()
                    tr.amount = self.get_amount(hist['instructions'], data)
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
        if data['total'] > data['params']['limit'] * (data['params']['offset'] + 1):
            offset=data['params']['offset']
            self.url=self.url.replace('&offset='+str(offset),'&offset='+str(offset+1))
            data['params']['offset'] += 1
            raise NextPage(self.url)
