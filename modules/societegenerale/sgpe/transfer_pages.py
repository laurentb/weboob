# -*- coding: utf-8 -*-

# Copyright(C) 2018      Sylvie Ye
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


import json
from datetime import date

from weboob.browser.pages import LoggedPage, HTMLPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.html import Attr
from weboob.capabilities.bank import Recipient
from weboob.browser.filters.json import Dict


class RecipientsJsonPage(LoggedPage, JsonPage):
    def is_all_external_recipient(self):
        return (
            Dict('donnees/nbTotalDestinataires')(self.doc) == len(self.doc['donnees']['items'])
            and not Dict('donnees/moreItems')(self.doc)
        )

    @method
    class iter_external_recipients(DictElement):
        item_xpath = 'donnees/items'

        class item(ItemElement):
            klass = Recipient

            def condition(self):
                return Dict('coordonnee/0/natureTypee')(self) == 'CREDIT'

            obj_category = 'Externe'
            obj_id = Dict('coordonnee/0/refSICoordonnee')
            obj_iban = Dict('coordonnee/0/numeroCompte')
            obj_label = obj__account_title = Dict('nomRaisonSociale')
            obj_enabled_at = date.today()


class EasyTransferPage(LoggedPage, HTMLPage):
    def update_origin_account(self, origin_account):
        for account in self.doc.xpath('//ul[@id="idCptFrom"]//li'):
            # get all account data
            data = Attr('.', 'data-comptecomplet')(account)
            json_data = json.loads(data.replace('&quot;', '"'))

            if (
                origin_account.label == json_data['libelleCompte']
                and origin_account.iban == json_data['ibanCompte']
            ):
                origin_account._product_code = json_data['codeProduit']
                origin_account._underproduct_code = json_data['codeSousProduit']
                break
        else:
            assert False, 'Account % not found on transfer page' % (origin_account.label)

    def iter_internal_recipients(self):
        if self.doc.xpath('//ul[@id="idCmptToInterne"]'):
            for account in self.doc.xpath('//ul[@id="idCmptToInterne"]/li'):
                data = Attr('.', 'data-comptecomplet')(account)
                json_data = json.loads(data.replace('&quot;', '"'))

                rcpt = Recipient()
                rcpt.category = 'Interne'
                rcpt.id = rcpt.iban = json_data['ibanCompte']
                rcpt.label = json_data['libelleCompte']
                rcpt.enabled_at = date.today()

                yield rcpt
