# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from datetime import datetime

from weboob.browser.pages import LoggedPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanDecimal, Env, Format, Currency, Field, Eval,
)
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import Bill, Subscription


class LoginPage(JsonPage):
    @property
    def logged(self):
        return self.doc['result'] == 'success'


class SubscriptionsPage(LoggedPage, JsonPage):
    @method
    class get_subscription(ItemElement):
        klass = Subscription

        obj_id = Eval(str, Dict('data/user/current_account_id'))
        obj_subscriber = Dict('data/user/display_name')
        obj_label = Dict('data/user/display_name')


class DocumentsPage(LoggedPage, JsonPage):
    @pagination
    @method
    class iter_documents(DictElement):
        item_xpath = 'data'

        def next_page(self):
            doc = self.page.doc
            current_page = int(doc['page'])
            if current_page >= doc['pages']:
                return

            params = {
                'ajax': 'true',
                'order_by': 'name',
                'order_for[name]': 'asc',
                'page': current_page + 1,
                'per_page': '100'
            }
            return self.page.browser.documents.build(subid=self.env['subid'], params=params)

        class item(ItemElement):
            klass = Bill

            _num = Dict('document/id')

            obj_id = Format('%s_%s', Env('subid'), _num)
            obj_date = Eval(datetime.fromtimestamp, Dict('created_at'))
            obj_label = Format('Facture %s', Field('id'))
            obj_url = Dict('document/href')
            obj_price = CleanDecimal(Dict('amount/amount'))
            obj_currency = Currency(Dict('amount/currency'))
            obj_format = 'pdf'
