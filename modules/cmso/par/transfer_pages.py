# -*- coding: utf-8 -*-

# Copyright(C) 2019      Sylvie Ye
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

from __future__ import unicode_literals

import datetime as dt

from weboob.browser.pages import JsonPage, LoggedPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Recipient
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


class TransferInfoPage(LoggedPage, JsonPage):
    def get_numbers(self):
        # If account information is not available when asking for the
        # recipients (server error for ex.), return an empty dictionary
        # that will be filled later after being returned the json of the
        # account page (containing the accounts IDs too).
        if 'listCompteTitulaireCotitulaire' not in self.doc and 'exception' in self.doc:
            return {}

        ret = {}

        ret.update({
            d['index']: d['numeroContratSouscrit']
            for d in self.doc['listCompteTitulaireCotitulaire']
        })
        ret.update({
            d['index']: d['numeroContratSouscrit']
            for p in self.doc['listCompteMandataire'].values()
            for d in p
        })
        ret.update({
            d['index']: d['numeroContratSouscrit']
            for p in self.doc['listCompteLegalRep'].values()
            for d in p
        })

        return ret

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

        class item(ItemElement):
            klass = Recipient

            obj_id = obj_iban = Dict('iban')
            obj_label = Dict('nom')
            obj_category = 'Externe'
            obj_enabled_at = dt.date.today()
            obj__index = Dict('index')

            def condition(self):
                return Dict('actif', default=False)(self)
