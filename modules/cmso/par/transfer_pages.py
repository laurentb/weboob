# -*- coding: utf-8 -*-

# Copyright(C) 2019      Sylvie Ye
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

import datetime as dt

from weboob.browser.pages import JsonPage, LoggedPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Recipient, Transfer, TransferBankError
from weboob.capabilities.base import NotAvailable


class MyRecipientItemElement(ItemElement):
    def condition(self):
        return Dict('eligibiliteCredit', default=False)

    klass = Recipient

    obj_id = Dict('numeroContratSouscrit')
    obj_label = Dict('lib')
    obj_iban = NotAvailable
    obj_enabled_at = dt.date.today()
    obj_category = 'Interne'
    obj__index = Dict('index')


class RecipientsListPage(LoggedPage, JsonPage):
    def get_rcpt_index(self, recipient):
        if recipient.category == 'Externe':
            for el in self.doc['listBeneficiaries']:
                for rcpt in el:
                    # in this list, recipient iban is like FR111111111111111XXXXX
                    if rcpt['iban'][:-5] == recipient.iban[:-5] and rcpt['nom'] == recipient.label:
                        return rcpt['index']
        return recipient._index


class TransferInfoPage(LoggedPage, JsonPage):
    def get_transfer_info(self, info):
        # If account information is not available when asking for the
        # recipients (server error for ex.), return an empty dictionary
        # that will be filled later after being returned the json of the
        # account page (containing the accounts IDs too).
        if 'listCompteTitulaireCotitulaire' not in self.doc and 'exception' in self.doc:
            return {}

        information = {
            'numbers': ('index', 'numeroContratSouscrit'),
            'eligibilite_debit': ('numeroContratSouscrit', 'eligibiliteDebit'),
        }
        key = information[info][0]
        value = information[info][1]

        ret = {}
        ret.update({
            d[key]: d[value]
            for d in self.doc['listCompteTitulaireCotitulaire']
        })
        ret.update({
            d[key]: d[value]
            for p in self.doc['listCompteMandataire'].values()
            for d in p
        })
        ret.update({
            d[key]: d[value]
            for p in self.doc['listCompteLegalRep'].values()
            for d in p
        })
        return ret

    def get_numbers(self):
        return self.get_transfer_info('numbers')

    def get_eligibilite_debit(self):
        return self.get_transfer_info('eligibilite_debit')

    @method
    class iter_titu_accounts(DictElement):
        item_xpath = 'listCompteTitulaireCotitulaire'

        class item(MyRecipientItemElement):
            pass

    @method
    class iter_manda_accounts(DictElement):
        item_xpath = 'listCompteMandataire/*'

        class item(MyRecipientItemElement):
            pass

    @method
    class iter_legal_rep_accounts(DictElement):
        item_xpath = 'listCompteLegalRep/*'

        class item(MyRecipientItemElement):
            pass

    @method
    class iter_external_recipients(DictElement):
        item_xpath = 'listBeneficiaries'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Recipient

            obj_id = obj_iban = Dict('iban')
            obj_label = Dict('nom')
            obj_category = 'Externe'
            obj_enabled_at = dt.date.today()
            obj__index = Dict('index')

            def condition(self):
                return Dict('actif', default=False)(self)


class TransferPage(LoggedPage, JsonPage):
    def on_load(self):
        if self.doc.get('exception') and not self.doc.get('debitAccountOwner'):
            if Dict('exception/type')(self.doc) == 1:
                # technical error
                assert False, 'Error with code %s occured during init_transfer: %s' % \
                    (Dict('exception/code')(self.doc), Dict('exception/message')(self.doc))
            elif Dict('exception/type')(self.doc) == 2:
                # user error
                raise TransferBankError(message=Dict('exception/message')(self.doc))

    def handle_transfer(self, account, recipient, amount, reason, exec_date):
        transfer = Transfer()
        transfer.amount = CleanDecimal(Dict('amount'))(self.doc)
        transfer.currency = Currency(Dict('codeDevise'))(self.doc)
        transfer.label = reason

        if exec_date:
            transfer.exec_date = dt.date.fromtimestamp(int(Dict('date')(self.doc))//1000)

        transfer.account_id = account.id
        transfer.account_label = CleanText(Dict('debitAccountLabel'))(self.doc)
        transfer.account_balance = CleanDecimal(Dict('debitAccountBalance'))(self.doc)

        transfer.recipient_id = recipient.id
        transfer.recipient_iban = recipient.iban
        transfer.recipient_label = CleanText(Dict('creditAccountOwner'))(self.doc)

        return transfer

    def get_transfer_confirm_id(self):
        return self.doc.get('numeroOperation')
