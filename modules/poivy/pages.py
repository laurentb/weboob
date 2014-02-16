# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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

from weboob.tools.browser import BasePage
from weboob.capabilities.bill import Subscription, Detail
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time

import re

__all__ = ['LoginPage', 'HomePage', 'HistoryPage', 'BillsPage', 'ErrorPage']


class ErrorPage(BasePage):
    def on_loaded(self):
        pass


class LoginPage(BasePage):
    def on_loaded(self):
        pass

    def _predicate_form(self, form):
        try:
            return form.attrs['class'] == "form-detail"
        except:
            return False

    def login(self, login, password):
        captcha = self.document.xpath('//label[@class="label_captcha_input"]')
        if len(captcha) > 0:
            return False

        form_newsletter = self.document.xpath('//form[@id="newsletter_form"]')[0]
        hidden_input = form_newsletter.xpath('./input[@type="hidden"]')[0]
        hidden_id = hidden_input.attrib["value"]
        hidden_name = hidden_input.attrib["name"]

        # Form without name
        self.browser.select_form(predicate=self._predicate_form)
        self.browser.set_all_readonly(False)
        self.browser['login[username]'] = login.encode('iso-8859-1')
        self.browser['login[password]'] = password.encode('iso-8859-1')
        self.browser[hidden_name] = hidden_id
        self.browser.submit(nologin=True)
        return True


class HomePage(BasePage):
    def on_loaded(self):
        pass

    def get_list(self):
        spanabo = self.document.xpath('//span[@class="welcome-text"]/b')[0]
        owner = spanabo.text_content()
        credit = self.document.xpath('//span[@class="balance"]')[0].text_content()

        subscription = Subscription(owner)
        subscription.label = u"Poivy - %s - %s" % (owner, credit)
        subscription._balance = Decimal(re.sub(u'[^\d\-\.]', '', credit))

        return [subscription]


class HistoryPage(BasePage):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def on_loaded(self):
        pass

    def get_calls(self):
        table = self.document.xpath('//table/tbody')[0]
        for tr in table.xpath('tr'):
            tds = tr.xpath('td')

            rawdate = tds[0].text_content()
            splitdate = rawdate.split('-')
            month_no = self.months.index(splitdate[1]) + 1
            mydate = date(int(splitdate[2]), month_no, int(splitdate[0]))

            rawtime = tds[1].text_content()
            mytime = time(*[int(x) for x in rawtime.split(":")])

            price = re.sub(u'[^\d\-\.]', '', tds[6].text)
            detail = Detail()
            detail.datetime = datetime.combine(mydate, mytime)
            detail.label = u"%s from %s to %s - %s" % (tds[2].text, tds[3].text, tds[4].text, tds[5].text)
            try:
                detail.price = Decimal(price)
            except InvalidOperation:
                detail.price = Decimal(0)  # free calls
            detail.currency = 'EUR'

            yield detail


class BillsPage(BasePage):
    def on_loaded(self):
        pass
