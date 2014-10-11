# -*- coding: utf-8 -*-

# Copyright(C) 2012 Florent Fourcot
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

from datetime import date
from weboob.capabilities.library import Book, Renew
from weboob.deprecated.browser import Page
from weboob.deprecated.mech import ClientForm
from weboob.tools.html import html2text


class SkipPage(Page):
    pass


class HomePage(Page):
    def on_loaded(self):
        link = self.document.find('//a[@id="patronRSSFeedLinkComponent"]')
        self.id = link.attrib['href'].split('/')[4]

    def get_id(self):
        return self.id


def txt2date(s):
    split = s.split('-')
    return date(int(split[2]) + 2000, int(split[1]), int(split[0]))


class RentedPage(Page):
    def get_list(self):
        for tr in self.document.getroot().xpath('//tr[@class="patFuncEntry"]'):
            id = tr.xpath('td/input')[0].attrib["value"]
            book = Book(id)
            bigtitle = tr.xpath('td[@class="patFuncTitle"]/label/a')[0].text
            book.name = bigtitle.split('/')[0]
            book.author = bigtitle.split('/')[1]
            date = tr.xpath('td[@class="patFuncStatus"]')[0].text
            book.date = txt2date(date.replace('RETOUR', ''))
            yield book

    def renew(self, id):
        # find the good box
        input = self.document.find('//input[@value="%s"]' % id)
        self.browser.select_form("checkout_form")
        self.browser.form.set_all_readonly(False)
        self.browser.controls.append(ClientForm.TextControl('text', input.attrib['name'], {'value': id}))
        self.browser.controls.append(ClientForm.TextControl('text', 'requestRenewSome', {'value': 'requestRenewSome'}))
        self.browser.submit()

    def confirm_renew(self):
        self.browser.select_form("checkout_form")
        self.browser.form.set_all_readonly(False)
        self.browser.submit(name='renewsome')

    def read_renew(self, id):
        for tr in self.document.getroot().xpath('//tr[@class="patFuncEntry"]'):
            if len(tr.xpath('td/input[@value="%s"]' % id)) > 0:
                message = self.browser.parser.tostring(tr.xpath('td[@class="patFuncStatus"]')[0])
                renew = Renew(id)
                renew.message = html2text(message).replace('\n', '')
                return renew


class HistoryPage(Page):
    pass


class BookedPage(Page):
    # TODO: book some books...
    pass


class LoginPage(Page):
    def login(self, login, passwd):
        self.browser.select_form(nr=0)
        self.browser.form.set_all_readonly(False)
        self.browser['code'] = login
        self.browser['pin'] = passwd
        self.browser.submit()
