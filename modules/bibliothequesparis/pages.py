# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanText, Date, Regexp, Field
from weboob.browser.filters.html import Link
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import UserError
from weboob.capabilities.library import Book


class LoginPage(JsonPage):
    @property
    def logged(self):
        return self.doc['success']


class JsonMixin(JsonPage):
    def on_load(self):
        if not self.doc['success']:
            for err in self.doc.get('errors', []):
                raise Exception(err['msg'])

        if isinstance(self.doc['d'], list) and self.doc['d']:
            msg = self.doc['d'][0].get('ErrorMessage')
            if msg:
                raise UserError(msg)


class LoansPage(LoggedPage, JsonMixin):
    def __init__(self, browser, response, *args, **kwargs):
        super(LoansPage, self).__init__(browser, response, *args, **kwargs)
        self.sub = self.sub_class(browser, response, data=self.sub_data)

    @property
    def sub_data(self):
        if isinstance(self.doc['d'], dict):
            return b''
        return self.doc['d'].encode('utf-8')

    class sub_class(HTMLPage):
        data = None

        def __init__(self, browser, response, data):
            self.data = data
            super(LoansPage.sub_class, self).__init__(browser, response)

        @method
        class get_loans(ListElement):
            item_xpath = '//div[@id="loans-box"]//li[has-class("loan-item")]'

            class item(ItemElement):
                klass = Book

                obj_url = Link('.//div[@class="loan-custom-result"]/a')
                obj_id = Regexp(Field('url'), r'/SYRACUSE/(\d+)/')
                obj_name = CleanText('.//h3[has-class("title")]')
                # warning: date span may also contain "(à rendre bientôt)" along with date
                obj_date = Date(Regexp(CleanText('.//li[has-class("dateretour")]/span[@class="loan-info-value"]'), r'(\d+/\d+/\d+)'), dayfirst=True)
                obj_location = CleanText('.//li[has-class("localisation")]//span[@class="loan-info-value"]')
                obj_author = Regexp(CleanText('.//div[@class="loan-custom-result"]//p[@class="template-info"]'), '^(.*?) - ')
                obj__renew_data = CleanText('.//span[has-class("loan-data")]')


class RenewPage(LoggedPage, JsonMixin):
    pass


class SearchPage(LoggedPage, JsonPage):
    @method
    class iter_books(DictElement):
        item_xpath = 'd/Results'

        class item(ItemElement):
            klass = Book

            obj_url = Dict('FriendlyUrl')
            obj_id = Dict('Resource/RscId')
            obj_name = Dict('Resource/Ttl')
            obj_author = Dict('Resource/Crtr', default=None)

    def get_max_page(self):
        return self.doc['d']['SearchInfo']['PageMax']
