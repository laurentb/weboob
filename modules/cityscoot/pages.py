# -*- coding: utf-8 -*-

# Copyright(C) 2017      P4ncake
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


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, Env, Regexp, Format, Date, Async, AsyncLoad
from weboob.browser.filters.html import Link
from weboob.capabilities.bill import DocumentTypes, Bill, Subscription
from weboob.capabilities.base import NotAvailable

class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(id='UserLoginForm')

        form['data[User][email]'] = login
        form['data[User][password]'] = password

        form.submit()

    def get_error(self):
        return CleanText('//div[contains(text(), "Erreur")]')(self.doc)


class SubscriptionsPage(LoggedPage, HTMLPage):
    @method
    class get_item(ItemElement):
        klass = Subscription

        obj_subscriber = Regexp(CleanText('//label[contains(text(), "Prénom")]/../text()'), r'(\D*)')
        obj_label = CleanText('//td[contains(text(), "Adresse email")]/../td[2]')

        def obj_id(self):
            return Regexp(CleanText('//label[contains(text(), "Prénom")]/../text()'), r'(\d*$)')(self)


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class iter_documents(TableElement):
        item_xpath = '//table//tr[position() > 1]'
        head_xpath = '//table//tr/th'

        class item(ItemElement):
            klass = Bill

            load_details = Link('.//a[contains(text(), "VOIR")]') & AsyncLoad

            obj_id = Format('%s_%s', Env('subid'), Regexp(CleanText('.//a[contains(text(), "VOIR")]/@href'), r'(\d*$)'))
            obj_url = Link('.//a[contains(text(), "VOIR")]', default=NotAvailable)
            obj_date = Async('details') & Date(Regexp(CleanText('.//h3'), r'(\d{2}\/\d{2}\/\d{4})'), dayfirst=True)
            obj_format = 'html'
            obj_label = Async('details') & CleanText('.//h3')
            obj_type = DocumentTypes.BILL
            obj_price = Async('details') & CleanDecimal('.//td[.="Total"]/following-sibling::td')
            obj_vat = Async('details') & CleanDecimal('.//td[contains(text(), "TVA")]/following-sibling::td')
            obj_currency = u'EUR'
