# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Format, Field,
    Regexp, Slugify, DateGuesser
)
from weboob.capabilities.bill import Bill, Subscription
from weboob.capabilities.base import NotAvailable
from weboob.tools.date import LinearDateGuesser
from datetime import timedelta


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def get_error(self):
        return CleanText('//li[@class="notification-summary-message-error"][1]')(self.doc)


class SubscriptionsPage(LoggedPage, HTMLPage):
    @method
    class iter_subscriptions(ListElement):
        item_xpath = '//ul[@id="navSideProducts"]/li'

        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('//span[@class="wording"]')
            obj_id = CleanText('./a/p', replace=[('N° ', '')])
            obj_label = obj_id

            # Every subscription a product token and a type ex: card = 240
            obj__product_token = Regexp(CleanText('./@id'), r'navSideProduct_(\d*)')
            obj__product_type = Regexp(CleanText('(//div[@class="logo"])[1]//img/@src'), "/img/product_(\d*).png")


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class iter_documents(ListElement):
        item_xpath = '(//table[contains(@class, "table-transaction")])[1]/tbody/tr'

        class item(ItemElement):
            klass = Bill

            # We have no better id than date-hour-marketname slugified
            obj__newid = Format('%s%s%s',
                                CleanText('.//span[contains(., "/")]', replace=[('/', '')]),
                                Regexp(CleanText('.//h3', replace=[('h', '')]), '(.*) - '),
                                CleanText('.//h3/strong'))
            obj_id = Slugify(Field('_newid'))
            obj_date = DateGuesser(CleanText('.//span[contains(., "/")]'), LinearDateGuesser(date_max_bump=timedelta(45)))
            obj_label = Format('Facture %s', CleanText('.//h3/strong'))
            obj_type = 'bill'
            obj_price = MyDecimal('./td[@class="al-r"]')
            obj_currency = "€"
