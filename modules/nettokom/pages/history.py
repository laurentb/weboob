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


from datetime import datetime, date, time
from decimal import Decimal

from weboob.deprecated.browser import Page
from weboob.capabilities.bill import Detail


class DetailsPage(Page):

    def on_loaded(self):
        self.details = []
        table = self.document.xpath('//table[@id="reportTable"]')

        if len(table) > 0:
            for tr in table[0].xpath('tbody/tr'):
                detail = Detail()
                # Skip global category
                if tr.find('td/a') is not None:
                    continue
                if tr.attrib["class"] == "totalAmount":
                    continue
                tds = tr.xpath('td')
                detail.label = unicode(tds[0].text.strip())
                detail.infos = unicode(tds[1].text.strip())
                detail.price = Decimal(tds[2].text.split(' ')[0].replace(',', '.'))

                self.details.append(detail)

    def get_details(self):
        return self.details


def _get_date(detail):
    return detail.datetime


class BillsPage(Page):
    def on_loaded(self):
        pass


class HistoryPage(Page):

    def on_loaded(self):
        self.calls = []
        for tr in self.document.xpath('//tr'):
            try:
                attrib = tr.attrib["class"]
            except:
                continue
            if attrib == "even" or attrib == "odd":
                label = u''
                tddate = tr.find('td[@class="middle nowrap"]')
                for td in tr.xpath('td[@class="long"]'):
                    label += unicode(td.text.strip()) + u' '
                tdprice = tr.xpath('td[@class="price"]')
                label += u'(' + unicode(tdprice[0].text.strip()) + u')'
                price = Decimal(tdprice[1].text.strip().replace(',', '.'))
                detail = Detail()
                mydate = date(*reversed([int(x) for x in tddate.text.strip().split(' ')[0].split(".")]))
                mytime = time(*[int(x) for x in tddate.text.strip().split(' ')[1].split(":")])
                detail.datetime = datetime.combine(mydate, mytime)
                detail.label = label
                detail.price = price

                self.calls.append(detail)

    def get_calls(self):
        return sorted(self.calls, key=_get_date, reverse=True)
