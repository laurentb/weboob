# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

from datetime import date
from decimal import Decimal

from weboob.capabilities.bank import Account, Transaction
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import DomainBrowser


__all__ = ['BredBrowser']


class BredBrowser(DomainBrowser):
    BASEURL = 'https://www.bred.fr'

    def __init__(self, accnum, login, password, *args, **kwargs):
        super(BredBrowser, self).__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.accnum = accnum

        self.do_login(login, password)

    def do_login(self, login, password):
        self.location('/transactionnel/Authentication', data={'identifiant': login, 'password': password})

        if 'gestion-des-erreurs/erreur-pwd' in self.url:
            raise BrowserIncorrectPassword('Bad login/password.')
        if 'gestion-des-erreurs/opposition' in self.url:
            raise BrowserIncorrectPassword('Your account is disabled')

    ACCOUNT_TYPES = {'000': Account.TYPE_CHECKING,
                     '999': Account.TYPE_MARKET,
                     '011': Account.TYPE_CARD,
                     '023': Account.TYPE_SAVINGS,
                     '078': Account.TYPE_SAVINGS,
                     '080': Account.TYPE_SAVINGS,
                     '027': Account.TYPE_SAVINGS,
                     '037': Account.TYPE_SAVINGS,
                    }
    def get_accounts_list(self):
        r = self.open('/transactionnel/services/rest/Account/accounts')

        for content in r.json()['content']:
            if self.accnum != '00000000000' and content['numero'] != self.accnum:
                continue
            for poste in content['postes']:
                a = Account()
                a._number = content['numeroLong']
                a._nature = poste['codeNature']
                a._consultable = poste['consultable']
                a.id = '%s.%s' % (a._number, a._nature)
                a.type = self.ACCOUNT_TYPES.get(poste['codeNature'], Account.TYPE_UNKNOWN)

                if poste['postePortefeuille']:
                    a.label = u'Portefeuille Titres'
                    a.balance = Decimal(str(poste['montantTitres']['valeur']))
                    a.currency = poste['montantTitres']['monnaie']['code'].strip()
                    yield a

                if not 'libelle' in poste:
                    continue

                a.label = ' '.join([content['intitule'].strip(), poste['libelle'].strip()])
                a.balance = Decimal(str(poste['solde']['valeur']))
                a.currency = poste['solde']['monnaie']['code'].strip()
                yield a

    def get_history(self, account):
        if not account._consultable:
            raise NotImplementedError()

        offset = 0
        next_page = True
        while next_page:
            r = self.open('/transactionnel/services/applications/operations/get/%(number)s/%(nature)s/00/%(currency)s/%(startDate)s/%(endDate)s/%(offset)s/%(limit)s' %
                          {'number': account._number,
                           'nature': account._nature,
                           'currency': account.currency,
                           'startDate': '2000-01-01',
                           'endDate': date.today().strftime('%Y-%m-%d'),
                           'offset': offset,
                           'limit': 50
                          })
            next_page = False
            offset += 50
            for op in r.json()['content']['operations']:
                next_page = True
                t = Transaction()
                t.id = op['id']
                t.amount = Decimal(str(op['montant']))
                t.date = date.fromtimestamp(op.get('dateDebit', op.get('dateOperation'))/1000)
                t.rdate = date.fromtimestamp(op.get('dateOperation', op.get('dateDebit'))/1000)
                t.vdate = date.fromtimestamp(op.get('dateValeur', op.get('dateDebit', op.get('dateOperation')))/1000)
                if 'categorie' in op:
                    t.category = op['categorie']
                t.label = op['libelle']
                t.raw = ' '.join([op['libelle']] + op['details'])
                yield t
