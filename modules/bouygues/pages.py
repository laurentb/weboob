# -*- coding: utf-8 -*-
# Copyright(C) 2010-2015 Bezleputh
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

from weboob.capabilities.messages import CantSendMessage

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanDecimal, CleanText, Regexp


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@id="log_data"]')
        form['username'] = login
        form['password'] = password
        form.submit()


class LoginSuccess(HTMLPage, LoggedPage):
    pass


class SendSMSPage(HTMLPage):
    def send_sms(self, message, receivers):
        sms_number = CleanDecimal(Regexp(CleanText('//span[@class="txt12-o"][1]/strong'), '(\d*) SMS.*'))(self.doc)
        if sms_number == 0:
            msg = CleanText('//span[@class="txt12-o"][1]')(self.doc)
            raise CantSendMessage(msg)

        form = self.get_form('//form[@name="formSMS"]')
        form["fieldMsisdn"] = receivers
        form["fieldMessage"] = message.content
        form.submit()


class SendSMSErrorPage(HTMLPage):
    def get_error_message(self):
        return CleanText('//span[@class="txt12-o"][1]')(self.doc)
