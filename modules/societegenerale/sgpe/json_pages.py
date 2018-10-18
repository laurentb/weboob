# -*- coding: utf-8 -*-

# Copyright(C) 2016     Baptiste Delpey
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

import requests
from datetime import datetime

from weboob.browser.pages import LoggedPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, CleanText, Date, Format, BrowserURL, Env
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import Currency
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.capabilities.bill import Document, Subscription
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.compat import quote_plus

from .pages import Transaction

class AccountsJsonPage(LoggedPage, JsonPage):
    ENCODING = 'utf-8'

    TYPES = {u'COMPTE COURANT':      Account.TYPE_CHECKING,
             u'COMPTE PERSONNEL':    Account.TYPE_CHECKING,
             u'CPTE PRO':            Account.TYPE_CHECKING,
             u'CPTE PERSO':          Account.TYPE_CHECKING,
             u'CODEVI':              Account.TYPE_SAVINGS,
             u'CEL':                 Account.TYPE_SAVINGS,
             u'Ldd':                 Account.TYPE_SAVINGS,
             u'Livret':              Account.TYPE_SAVINGS,
             u'PEL':                 Account.TYPE_SAVINGS,
             u'Plan Epargne':        Account.TYPE_SAVINGS,
             u'PEA':                 Account.TYPE_PEA,
             u'Prêt':                Account.TYPE_LOAN,
            }

    def iter_accounts(self):
        for classeur in self.doc.get('donnees', {}).get('classeurs', {}):
            title = classeur['title']
            for compte in classeur.get('comptes', []):
                a = Account()
                a.label = CleanText().filter(compte['libelle'])
                a._id = compte['id']
                a.type = self.obj_type(a.label)
                a.number = compte['iban'].replace(' ', '')
                # for some account that don't have Iban the account number is store under this variable in the Json
                if not is_iban_valid(a.number):
                    a.iban = NotAvailable
                else:
                    a.iban = a.number
                # id based on iban to match ids in database.
                a.id = a.number[4:-2] if len(a.number) == 27 else a.number
                a._agency = compte['agenceGestionnaire']
                a._title = title
                yield a

    def obj_type(self, label):
        for wording, acc_type in self.TYPES.items():
            if wording.lower() in label.lower():
                return acc_type
        return Account.TYPE_CHECKING

    def get_error(self):
        if self.doc['commun']['statut'] == 'nok':
            # warning: 'nok' is case sensitive, for wrongpass at least it's 'nok'
            # for certain other errors (like no accounts), it's 'NOK'
            return self.doc['commun']['raison']
        return None


class BalancesJsonPage(LoggedPage, JsonPage):
    def on_load(self):
        if self.doc['commun']['statut'] == 'NOK':
            reason = self.doc['commun']['raison']
            if reason == 'SYD-COMPTES-UNAUTHORIZED-ACCESS':
                raise BrowserIncorrectPassword("Vous n'avez pas l'autorisation de consulter : {}".format(reason))
            raise BrowserUnavailable(reason)

    def populate_balances(self, accounts):
        for account in accounts:
            acc_dict = self.doc['donnees']['compteSoldesMap'][account._id]
            account.balance = CleanDecimal(replace_dots=True).filter(acc_dict['soldeComptable'])
            account.currency = Currency.get_currency(acc_dict['deviseSoldeComptable'])
            yield account


class HistoryJsonPage(LoggedPage, JsonPage):

    def get_value(self):
        if 'NOK' in self.doc['commun']['statut']:
            return 'position'
        else:
            return 'valeur'

    @pagination
    @method
    class iter_history(DictElement):
        def __init__(self, *args, **kwargs):
            super(DictElement, self).__init__(*args, **kwargs)
            self.item_xpath = 'donnees/compte/operations' if not 'Prochain' in self.page.url else 'donnees/ecritures'

        def condition(self):
            return 'donnees' in self.page.doc

        def next_page(self):
            d = self.page.doc['donnees']['compte'] if not 'Prochain' in self.page.url else self.page.doc['donnees']
            if 'ecrituresRestantes' in d:
                next_ope = d['ecrituresRestantes']
                next_data = d['sceauEcriture']
            else:
                next_ope = d['operationsRestantes']
                next_data = d['sceauOperation']
            if next_ope:
                data = {}
                data['b64e4000_sceauEcriture'] = next_data
                if not 'intraday' in self.page.url:
                    data['cl200_typeReleve'] = Env('value')(self)
                return requests.Request("POST", BrowserURL('history_next')(self), data=data)

        class item(ItemElement):
            klass = Transaction

            obj_rdate = Date(Dict('date', default=None), dayfirst=True, default=NotAvailable)
            obj_date = Date(Dict('dVl', default=None), dayfirst=True, default=NotAvailable)
            obj__coming = False

            # Label is split into l1, l2, l3, l4, l5.
            # l5 is needed for transfer label, for example:
            # 'l1': "000001 VIR EUROPEEN EMIS   NET"
            # 'l2': "POUR: XXXXXXXXXXXXX"
            # 'l3': "REF: XXXXXXXXXXXXXX"
            # 'l4': "REMISE: XXXXXX TRANSFER LABEL"
            # 'l5': "MOTIF: TRANSFER LABEL"
            obj_raw = Transaction.Raw(Format(
                '%s %s %s %s %s',
                Dict('l1'),
                Dict('l2'),
                Dict('l3'),
                Dict('l4'),
                Dict('l5'),
            ))

            # keep the 3 first rows for transaction label
            obj_label = Transaction.Raw(Format(
                '%s %s %s',
                Dict('l1'),
                Dict('l2'),
                Dict('l3'),
            ))

            def obj_amount(self):
                return CleanDecimal(Dict('c', default=None), replace_dots=True, default=None)(self) or \
                    CleanDecimal(Dict('d'), replace_dots=True)(self)

            def obj_deleted(self):
                return self.obj.type == FrenchTransaction.TYPE_CARD_SUMMARY


class BankStatementPage(LoggedPage, JsonPage):
    def get_min_max_date(self):
        criterium = self.doc['donnees']['criteres']
        return criterium['dateMin'], criterium['dateMax']

    @method
    class iter_subscription(DictElement):
        item_xpath = 'donnees/comptes'

        class item(ItemElement):
            klass = Subscription

            obj_id = Dict('id')
            obj_label = Dict('libelle')
            obj_subscriber = Env('subscriber')

    def iter_documents(self):
        account, = self.doc['donnees']['comptes']
        statements = account['releves']

        for document in statements:
            d = Document()
            d.date = datetime.strptime(document['dateEdition'], '%d/%m/%Y')
            d.label = '%s %s' % (account['libelle'], document['dateEdition'])
            d.type = 'document'
            d.format = 'pdf'
            d.id = '%s_%s' % (account['id'], document['dateEdition'].replace('/', ''))
            d.url = '/icd/syd-front/data/syd-rce-telechargerReleve.html?b64e4000_sceau=%s' % quote_plus(document['sceau'])

            yield d
