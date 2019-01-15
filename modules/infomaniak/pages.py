# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from datetime import datetime

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import (
    CleanDecimal, Env, Regexp, Format, Currency, Field, Eval,
)
from weboob.browser.filters.json import Dict
from weboob.capabilities.bill import DocumentTypes, Bill, Subscription
from weboob.tools.compat import urljoin


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
    @method
    class iter_documents(DictElement):
        item_xpath = 'aLines'

        class item(ItemElement):
            klass = Bill

            def obj_url(self):
                return urljoin(self.page.url, Regexp(Dict('sOperation'), r'&quot;(/.*\.pdf)')(self))

            _num = Regexp(Field('url'), r'facture_(\d+).pdf')

            obj_id = Format('%s_%s', Env('subid'), _num)
            obj_date = Eval(datetime.fromtimestamp, Dict('sTimestamp'))
            obj_label = Format('Facture %s', _num)
            obj_price = CleanDecimal(Dict('fMontant'))
            obj_currency = Currency(Dict('sMontant'))
            obj_type = DocumentTypes.BILL
            obj_format = 'pdf'
