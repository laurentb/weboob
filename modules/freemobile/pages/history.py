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

from weboob.tools.browser import BasePage
from weboob.capabilities.bill import Detail, Bill

import re

__all__ = ['HistoryPage', 'DetailsPage']


def convert_price(div):
    try:
        price = div.find('div[@class="horsForfait"]/p/span').text
        price = price.encode('utf-8', 'replace').replace('€', '').replace(',', '.')
        return Decimal(price)
    except:
        return Decimal(0)


class DetailsPage(BasePage):

    def on_loaded(self):
        self.details = {}
        self.datebills = []
        for div in self.document.xpath('//div[@class="infosLigne pointer"]'):
            phonenumber = div.text
            phonenumber = phonenumber.split("-")[-1].strip()
            virtualnumber = div.attrib['onclick'].split('(')[1][1]
            self.details['num' + str(phonenumber)] = virtualnumber

        for div in self.document.xpath('//div[@class="infosConso"]'):
            num = div.attrib['id'].split('_')[1][0]
            self.details[num] = []

            # National parsing
            divnat = div.xpath('div[@class="national"]')[0]
            self.parse_div(divnat, "National : %s | International : %s", num, False)

            # International parsing
            divint = div.xpath('div[@class="international hide"]')[0]
            self.parse_div(divint, u"Appels émis : %s | Appels reçus : %s", num, True)

        for trbill in self.document.xpath('//tr[@class="derniereFacture"]'):
            mydate = unicode(trbill.find('td').text.split(":")[1].strip())
            bill = Bill()
            bill.label = unicode(mydate)
            billid = mydate.replace('-', '')
            billid = billid[4:8] + billid[2:4] + billid[0:2]
            bill.id = phonenumber + "." + billid
            bill.date = date(*reversed([int(x) for x in mydate.split("-")]))
            alink = trbill.find('td/a')
            if alink.attrib.get("class") == "linkModal tips":
                bill.format = u'html'
                bill._url = alink.attrib.get('data-link')
            else:
                bill.format = u"pdf"
                bill._url = alink.attrib.get('href')
            self.datebills.append(bill)

    def parse_div(self, divglobal, string, num, inter=False):
        divs = divglobal.xpath('div[@class="detail"]')
        # Two informations in one div...
        div = divs.pop(0)
        voice = self.parse_voice(div, string, inter)
        self.details[num].append(voice)
        self.iter_divs(divs, num, inter)

    def iter_divs(self, divs, num, inter=False):
        for div in divs:
            detail = Detail()

            detail.label = unicode(div.find('div[@class="titre"]/p').text_content())
            if inter:
                detail.label = detail.label + u" (international)"
            detail.infos = unicode(div.find('div[@class="conso"]/p').text_content().lstrip())
            detail.price = convert_price(div)

            self.details[num].append(detail)

    def parse_voice(self, div, string, inter=False):
        voice = Detail()
        voice.label = unicode(div.find('div[@class="titre"]/p').text_content())
        if inter:
            voice.label = voice.label + " (international)"
        voice.price = convert_price(div)
        voice1 = div.xpath('div[@class="conso"]/p/span')[0].text
        voice2 = div.xpath('div[@class="conso"]/p/span')[1].text
        voice.infos = unicode(string) % (voice1, voice2)

        return voice

    def get_details(self, subscription):
        num = self.details['num' + subscription.id]
        return self.details[num]

    def date_bills(self):
        return self.datebills


def _get_date(detail):
    return detail.datetime


class HistoryPage(BasePage):

    def on_loaded(self):
        self.calls = []
        for tr in self.document.xpath('//tr'):
            tds = tr.xpath('td')
            if tds[0].text == None or tds[0].text == "Date":
                pass
            else:
                detail = Detail()
                mydate = date(*reversed([int(x) for x in tds[0].text.split(' ')[0].split("/")]))
                mytime = time(*[int(x) for x in tds[0].text.split(' ')[2].split(":")])
                detail.datetime = datetime.combine(mydate, mytime)
                detail.label = u' '.join([unicode(td.text.strip()) for td in tds[1:4] if td.text is not None])
                try:
                    detail.price = Decimal(tds[4].text[0:4].replace(',', '.'))
                except:
                    detail.price = Decimal(0)

                self.calls.append(detail)

    def get_calls(self, subscription):
        return sorted(self.calls, key=_get_date, reverse=True)
