# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


import datetime
from decimal import Decimal
import re

from weboob.deprecated.browser import Page
from weboob.capabilities.bank import Account

from ..transaction import Transaction


class LoginPage(Page):
    def login(self, login, passwd):
        self.browser.select_form(name='formIdentification')
        self.browser['noPersonne'] = login.encode(self.browser.ENCODING)
        self.browser['motDePasse'] = passwd.encode(self.browser.ENCODING)
        self.browser.submit(nologin=True)


class AccountsPage(Page):
    def get_list(self):
        names = set()
        for li in self.document.xpath('//div[@class="affichMontant"]/ul/li/a'):
            account = Account()
            account.label = unicode(li.cssselect('div.row-lib u')[0].text.strip())
            account.id = re.sub('[ \.\-]+', '', account.label)
            while account.id in names:
                account.id = account.id + '1'
            names.add(account.id)
            account.balance = Decimal(li.cssselect('p.row-right')[0].text.strip().replace(' ', '').replace(u'\xa0', '').replace(',', ''))
            account._link = li.attrib['href']
            yield account


class TransactionsPage(Page):
    months = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']

    def get_next_link(self):
        a = self.document.getroot().cssselect('div#nav-sub p.row-right a')
        if len(a) == 0:
            return None

        return a[0].attrib['href']

    def get_history(self):
        for div in self.document.xpath('//ol[@class="affichMontant"]/li/div'):
            t = Transaction(0)
            raw = div.xpath('.//div[@class="row-lib"]')[0].text
            date = div.xpath('.//span')[0].text.strip()
            m = re.match('(\d+)(er)? ([^ ]+)( \d+)?$', date)
            if m:
                dd = int(m.group(1))
                mm = self.months.index(m.group(3)) + 1
                if m.group(4) is not None:
                    yy = int(m.group(4))
                else:

                    d = datetime.date.today()
                    try:
                        d = d.replace(month=mm, day=dd)
                    except ValueError:
                        d = d.replace(year=d.year-1, month=mm, day=dd)

                    yy = d.year

                date = datetime.date(yy, mm, dd)
            else:
                self.logger.error('Unable to parse date %r' % date)
                continue

            t.parse(date, re.sub(r'[ ]+', ' ', raw))
            t.amount = Decimal(div.xpath('.//span')[-1].text.strip().replace(' ', '').replace(u'\xa0', '').replace(',', ''))

            yield t
