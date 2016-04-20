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

from weboob.browser.elements import ItemElement, method, TableElement
from weboob.browser.filters.standard import CleanText, CleanDecimal, TableCell
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
        t={'PEE':Account.TYPE_PEE, 'PEG':Account.TYPE_PEE, 'PERCO':Account.TYPE_PERCO}
        for acc in self.doc['positionTotaleDispositifDto']:
            ac = Account()
            ac.type = Account.TYPE_LIFE_INSURANCE
            ac.id = ac.number = acc['codeDispositif']
            ac.label = acc['libelleDispositif']
            ac._entreprise = acc['libelleEntreprise']
            ac.balance = Decimal(acc['mtBrut'])
            ac._ident = acc['idEnt']
            for k, v in t.items():
                if k in ac.label:
                    ac.type = v
                    break
            yield ac


class AccountDetailPage(LoggedPage, HTMLPage):
    def is_here(self):
        return bool(self.doc.xpath('//a[contains(.,"Consultation")]'))

    @method
    class iter_investments(TableElement):
        item_xpath = '//div[@class="table-responsive"]//tbody/tr'
        head_xpath = '//div[@class="table-responsive"]//thead/tr//th'
        col_sup = u'Support de placement'
        col_nbp = u'Nombre de parts'
        col_mtb = u'Montant brut'

        class item(ItemElement):
            def condition(self):
                acc = self.env['data']['acc']
                return CleanText().filter(self.el.xpath('./../../../preceding-sibling::h3')[-1]) == \
                       "%s [%s]" % (acc.label, acc._entreprise)

            klass = Investment

            def obj_label(self):
                try:
                    return CleanText(TableCell('sup'))(self).split('Valeur')[0]
                except IndexError:
                    return CleanText(TableCell('sup'))(self)

            def obj_unitvalue(self):
                try:
                    return Decimal(CleanText(TableCell('sup'))(self).split('Valeur')[1].split(':')[1].strip()[:-2])
                except IndexError:
                    return NotAvailable

            obj_quantity = CleanDecimal(TableCell('nbp'), default=NotAvailable)
            obj_valuation = CleanDecimal(TableCell('mtb'), replace_dots=True)

            def obj_vdate(self):
                try:
                    return datetime.strptime(CleanText(TableCell('sup'))(self).split('au')[1].split(':')[0].strip(),
                                             '%d/%m/%Y')
                except IndexError:
                    return NotAvailable

            obj_code = NotAvailable


class AccountHistoryPage(LoggedPage, JsonPage):
    @pagination
    def iter_history(self, data):
        for hist in self.doc['operationsIndividuelles']:
            if len(hist['instructions']) > 0:
                if hist['instructions'][0]['nomDispositif'] + hist['instructions'][0]['codeDispositif'] == data[
                    'acc'].label + data['acc'].id:
                    tr = Transaction()
                    tr.amount = Decimal(hist['montantNet']) + Decimal(hist['montantNetAbondement'])
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
