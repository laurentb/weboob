# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import datetime

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    Env, Field,
)
from weboob.capabilities.bank import Recipient


class DebitAccountsPage(LoggedPage, JsonPage):
    def get_debit_accounts_uid(self):
        return [Dict('uid')(recipient) for recipient in self.doc]


class CreditAccountsPage(LoggedPage, JsonPage):
    @method
    class iter_recipients(DictElement):
        class item(ItemElement):
            def condition(self):
                return Dict('uid')(self) != Env('acc_uid')(self)

            klass = Recipient

            def obj__is_internal_recipient(self):
                return bool(Dict('ledgerBalance', default=None)(self))

            obj_id = Dict('uid')
            obj_enabled_at = datetime.now().replace(microsecond=0)

            def obj_label(self):
                if Field('_is_internal_recipient')(self):
                    return Dict('type/label')(self)
                return Dict('owner')(self)

            def obj_category(self):
                if Field('_is_internal_recipient')(self):
                    return 'Interne'
                return 'Externe'
