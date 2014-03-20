# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014 Florent Fourcot
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

from weboob.tools.browser2.page import HTMLPage, LoggedPage, method, ListElement, ItemElement
from weboob.tools.browser2.filters import Env, CleanText, CleanDecimal, Field, Attr, Filter, Time, Date
from weboob.capabilities.bill import Subscription, Detail
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time

import re

__all__ = ['LoginPage', 'HomePage', 'HistoryPage', 'BillsPage', 'ErrorPage']


class ErrorPage(HTMLPage):
        pass


class LoginPage(HTMLPage):
    def _predicate_form(self, form):
        try:
            return form.attrs['class'] == "form-detail"
        except:
            return False

    def login(self, login, password):
        captcha = self.doc.xpath('//label[@class="label_captcha_input"]')
        if len(captcha) > 0:
            return False

        xpath_hidden = '//form[@id="newsletter_form"]/input[@type="hidden"]'
        hidden_id = Attr(xpath_hidden, "value")(self.doc)
        hidden_name = Attr(xpath_hidden, "name")(self.doc)

        form = self.get_form(xpath="//form[@class='form-detail']")
        form['login[username]'] = login.encode('iso-8859-1')
        form['login[password]'] = password.encode('iso-8859-1')
        form[hidden_name] = hidden_id
        form.submit()
        return True


class Insert2(Filter):
    """
    Insert two Filters inside a string
    """
    def __init__(self, selector, selector2, string):
        super(Insert2, self).__init__(selector)
        self.string = string
        self.selector2 = selector2

    def __call__(self, item):
        value = self.selector(item)
        value2 = self.selector2(item)
        return self.filter(value, value2)

    def filter(self, txt, txt2):
        return self.string % (txt, txt2)


class HomePage(LoggedPage, HTMLPage):

    @method
    class get_list(ListElement):
        item_xpath = '.'

        class item(ItemElement):
            klass = Subscription

            obj_id = CleanText('//span[@class="welcome-text"]/b')
            obj__balance = CleanDecimal(CleanText('//span[@class="balance"]'), replace_dots=False)
            obj_label = Insert2(Field('id'), Field('_balance'), u"Poivy - %s - %s €")


class HistoryPage(LoggedPage, HTMLPage):

    @method
    class get_calls(ListElement):
        item_xpath = '//table/tbody/tr'

        class item(ItemElement):
            klass = Detail

            obj_datetime = Env('datetime')
            obj_price = CleanDecimal('td[7]', replace_dots=False)
            obj_currency = u'EUR'
            obj_label = Env('label')

            def parse(self, el):
                tds = el.xpath('td')

                mydate = Date(CleanText('td[1]'))(el)
                mytime = Time(CleanText('td[2]'))(el)

                self.env['datetime'] = datetime.combine(mydate, mytime)
                self.env['label'] = u"%s from %s to %s - %s" % (tds[2].text, tds[3].text, tds[4].text, tds[5].text)


#TODO
class BillsPage(HTMLPage):
    pass
