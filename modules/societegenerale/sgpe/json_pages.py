# -*- coding: utf-8 -*-

# Copyright(C) 2016     Baptiste Delpey
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

import requests
from datetime import datetime

from weboob.browser.pages import LoggedPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanDecimal, CleanText, Date, Format, BrowserURL, Env,
    Field, Regexp, Currency as CurrencyFilter,
)
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import Currency, empty
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.bill import Document, Subscription, DocumentTypes
from weboob.exceptions import (
    BrowserUnavailable, NoAccountsException, BrowserPasswordExpired,
    AuthMethodNotImplemented,
)
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid
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

    @property
    def logged(self):
        return Dict('commun/raison', default=None)(self.doc) != "niv_auth_insuff"

    def on_load(self):
        if self.doc['commun']['statut'].lower() == 'nok':
            reason = self.doc['commun']['raison']
            if reason == 'SYD-COMPTES-UNAUTHORIZED-ACCESS':
                raise NoAccountsException("Vous n'avez pas l'autorisation de consulter : {}".format(reason))
            elif reason == 'niv_auth_insuff':
                return
            elif reason in ('chgt_mdp_oblig', 'chgt_mdp_init'):
                raise BrowserPasswordExpired('Veuillez vous rendre sur le site de la banque pour renouveler votre mot de passe')
            elif reason == 'oob_insc_oblig':
                raise AuthMethodNotImplemented("L'authentification par Secure Access n'est pas prise en charge")
            else:
                # the BrowserUnavailable was raised for every unknown error, and was masking the real error.
                # So users and developers didn't know what kind of error it was.
                assert False, 'Error %s is not handled yet.' % reason

    @method
    class iter_class_accounts(DictElement):
        item_xpath = 'donnees/classeurs'

        class iter_accounts(DictElement):
            @property
            def item_xpath(self):
                if 'intradayComptes' in self.el:
                    return 'intradayComptes'
                return 'comptes'

            class item(ItemElement):
                klass = Account

                obj__id = Dict('id')
                obj_number = CleanText(Dict('iban'), replace=[(' ', '')])
                obj_iban = Field('number')
                obj_label = CleanText(Dict('libelle'))
                obj__agency = Dict('agenceGestionnaire')

                def obj_id(self):
                    number = Field('number')(self)
                    if len(number) == 27:
                        # id based on iban to match ids in database.
                        return number[4:-2]
                    return number

                def obj_iban(self):
                    # for some account that don't have Iban the account number is store under this variable in the Json
                    number = Field('number')(self)
                    if not is_iban_valid(number):
                        return NotAvailable
                    return number

                def obj_type(self):
                    return self.page.acc_type(Field('label')(self))

    def acc_type(self, label):
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
                raise NoAccountsException("Vous n'avez pas l'autorisation de consulter : {}".format(reason))
            raise BrowserUnavailable(reason)

    def populate_balances(self, accounts):
        for account in accounts:
            acc_dict = self.doc['donnees']['compteSoldesMap'][account._id]
            account.balance = CleanDecimal(replace_dots=True).filter(acc_dict.get('soldeComptable', acc_dict.get('soldeInstantane')))
            account.currency = Currency.get_currency(acc_dict.get('deviseSoldeComptable', acc_dict.get('deviseSoldeInstantane')))
            account.coming = CleanDecimal(replace_dots=True, default=NotAvailable).filter(acc_dict.get('montantOperationJour'))
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

            obj_rdate = Env('rdate')
            obj_date = Env('date')
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

            def obj_commission(self):
                if Regexp(Field('label'), r' ([\d{1,3}\s?]*\d{1,3},\d{2}E COM [\d{1,3}\s?]*\d{1,3},\d{2}E)', default='')(self):
                    # commission can be scraped from labels like 'REMISE CB /14/08 XXXXXX YYYYYYYYYYY ZZ 105,00E COM 0,84E'
                    return CleanDecimal.French(Regexp(Field('label'), r'COM ([\d{1,3}\s?]*\d{1,3},\d{2})E', default=''), sign=lambda x: -1, default=NotAvailable)(self)
                return NotAvailable

            def obj_gross_amount(self):
                if not empty(Field('commission')(self)):
                    # gross_amount can be scraped from labels like 'REMISE CB /14/08 XXXXXX YYYYYYYYYYY ZZ 105,00E COM 0,84E'
                    return CleanDecimal.French(Regexp(Field('label'), r' ([\d{1,3}\s?]*\d{1,3},\d{2})E COM', default=''), default=NotAvailable)(self)
                return NotAvailable

            def obj_amount(self):
                return CleanDecimal(Dict('c', default=None), replace_dots=True, default=None)(self) or \
                    CleanDecimal(Dict('d'), replace_dots=True)(self)

            def obj_deleted(self):
                return self.obj.type == FrenchTransaction.TYPE_CARD_SUMMARY

            def parse(self, el):
                self.env['rdate'] = Date(Dict('date', default=None), dayfirst=True, default=NotAvailable)(self)
                self.env['date'] = Date(Dict('dVl', default=None), dayfirst=True, default=NotAvailable)(self)

                if 'REGULARISATION DE COMMISSION' in Dict('l1')(self) and self.env['date'] < self.env['rdate']:
                    # transaction corresponding a bank reimbursement were date and rdate are inverted
                    # ex: 24/07 in Dict('dVl'), but 24/09 is in Dict('date');
                    # so for this particular transaction the order should be 24/07 (rdate)
                    # while the effective date of credit on the account should be 27/09 (date)
                    self.env['rdate'], self.env['date'] = self.env['date'], self.env['rdate']


class BankStatementPage(LoggedPage, JsonPage):
    def get_min_max_date(self):
        min_date = Date(Dict('donnees/criteres/dateMin'), dayfirst=True, default=None)(self.doc)
        max_date = Date(Dict('donnees/criteres/dateMax'), dayfirst=True, default=None)(self.doc)
        assert min_date and max_date, 'There should have min date and max date to retrieve document'
        return min_date, max_date

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
            d.type = DocumentTypes.STATEMENT
            d.format = 'pdf'
            d.id = '%s_%s' % (account['id'], document['dateEdition'].replace('/', ''))
            d.url = '/icd/syd-front/data/syd-rce-telechargerReleve.html?b64e4000_sceau=%s' % quote_plus(document['sceau'])

            yield d


class MarketAccountPage(LoggedPage, JsonPage):
    @method
    class iter_market_accounts(DictElement):
        item_xpath = 'donnees/comptesTitresByClasseur'

        def condition(self):
            # Some 'comptesTitresByClasseur' do not have a 'list' key
            # and therefore have no account list, we skip them
            return Dict('list', default=None)(self)

        class iter_accounts(DictElement):
            item_xpath = 'list'

            class item(ItemElement):
                klass = Account

                obj__prestation_number = Dict('numeroPrestation')

                obj_id = Format('%s_TITRE', CleanText(Field('_prestation_number'), replace=[(' ', '')]))
                obj_number = CleanText(Field('_prestation_number'), replace=[(' ', '')])
                obj_label = Dict('intitule')
                obj_balance = CleanDecimal.French(Dict('evaluation'))
                obj_currency = CurrencyFilter(Dict('evaluation'))
                obj_type = Account.TYPE_MARKET


class MarketInvestmentPage(LoggedPage, JsonPage):
    @method
    class iter_investment(DictElement):
        item_xpath = 'donnees'

        class item(ItemElement):
            klass = Investment

            obj_label = Dict('libelle')
            obj_valuation = CleanDecimal.French(Dict('valorisation'))
            obj_quantity = CleanDecimal.French(Dict('quantite'))
            obj_unitvalue = CleanDecimal.French(Dict('cours'))

            def obj_code(self):
                code = Dict('codeISIN')(self)
                if is_isin_valid(code):
                    return code
                return NotAvailable

            def obj_code_type(self):
                if empty(Field('code')(self)):
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN
