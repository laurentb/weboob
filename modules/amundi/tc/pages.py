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

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage, pagination
from weboob.browser.pages import NextPage
from weboob.capabilities.bank import Account, Investment, Transaction


class FakePage(HTMLPage):
    pass


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        data = {'mail': login, 'password': passwd, 'connection': ''}

        self.browser.location('/home_priv_synth',
                              data=data,
                              headers={'Referer': 'https://epargnants.amundi-tc.com/home'})

    def is_here(self):
        return bool(self.doc.xpath('//div[@id="login-form"]'))


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


class AccountDetailPage(LoggedPage, JsonPage):
    # def is_here(self):
    #     return bool(self.doc.xpath(u'//span[contains(.,"Votre Épargne Salariale et Retraite")]'))

    def iter_investments(self,data):
        acc=data['acc']
        inv=Investment()
        for disp in self.doc['positionsSalarieDispositifDto']:
            if disp['codeDispositif']==acc.id:
                for ele in disp['positionsSalarieFondsDto']:
                    if ele['mtBrut']:
                        inv.label=ele['libelleFonds']
                        inv.code=ele['codeIsin']
                        inv.description=inv.label
                        inv.quantity=Decimal(ele['nbParts'])
                        inv.unitvalue = Decimal(ele['vl'])
                        inv.valuation = inv.unitvalue*inv.quantity
                        inv.diff = Decimal(ele['mtPMV'])
                        yield inv

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
                    yield tr

        if data['total'] > data['params']['limit'] * (data['params']['offset'] + 1):
            offset=data['params']['offset']
            self.url=self.url.replace('&offset='+str(offset),'&offset='+str(offset+1))
            data['params']['offset'] += 1
            raise NextPage(self.url)
