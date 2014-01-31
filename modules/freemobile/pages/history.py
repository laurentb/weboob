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


import re
import calendar
from datetime import datetime, date, time
from decimal import Decimal

from weboob.tools.browser import BasePage
from weboob.capabilities.bill import Detail, Bill


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
        self.datebills = {}
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
            if divint.xpath('div[@class="detail"]'):
                self.parse_div(divint, u"Appels émis : %s | Appels reçus : %s", num, True)

        for divbills in self.document.xpath('//div[@id="factContainer"]'):
            for divbill in divbills.xpath('.//div[@class="factLigne hide "]'):
                alink = divbill.xpath('.//div[@class="pdf"]/a')[0]
                localid = re.search('&l=(?P<id>\d*)&id',
                        alink.attrib.get('href')).group('id')
                mydate_str = re.search('&date=(?P<date>\d*)$',
                        alink.attrib.get('href')).group('date')
                mydate = datetime.strptime(mydate_str, "%Y%m%d").date()

                bill = Bill()
                bill.label = unicode(mydate_str)
                bill.id = unicode(mydate_str)
                bill.date = mydate
                bill.format = u"pdf"
                bill._url = alink.attrib.get('href')
                if "pdfrecap" in alink.attrib.get('href'):
                    bill.id = "recap-" + bill.id
                if localid not in self.datebills:
                    self.datebills[localid] = []
                self.datebills[localid].append(bill)

    def parse_div(self, divglobal, string, num, inter=False):
        divs = divglobal.xpath('div[@class="detail"]')
        # Two informations in one div...
        div = divs.pop(0)
        voice = self.parse_voice(div, string, num, inter)
        self.details[num].append(voice)
        self.iter_divs(divs, num, inter)

    def iter_divs(self, divs, num, inter=False):
        for div in divs:
            detail = Detail()

            detail.label = unicode(div.find('div[@class="titre"]/p').text_content())
            detail.id = "-" + detail.label.split(' ')[1].lower()
            if inter:
                detail.label = detail.label + u" (international)"
                detail.id = detail.id + "-inter"
            detail.infos = unicode(div.find('div[@class="conso"]/p').text_content().lstrip())
            detail.price = convert_price(div)

            self.details[num].append(detail)

    def parse_voice(self, div, string, num, inter=False):
        voice = Detail()
        voice.id = "-voice"
        voicediv = div.xpath('div[@class="conso"]')[0]
        voice.label = unicode(div.find('div[@class="titre"]/p').text_content())
        if inter:
            voice.label = voice.label + " (international)"
            voice.id = voice.id + "-inter"
        voice.price = convert_price(div)
        voice1 = voicediv.xpath('.//span[@class="actif"]')[0].text
        voice2 = voicediv.xpath('.//span[@class="actif"]')[1].text
        voice.infos = unicode(string) % (voice1, voice2)

        return voice

    def get_details(self, subscription):
        num = self.details['num' + subscription.id]
        for detail in self.details[num]:
            detail.id = subscription.id + detail.id
            yield detail

    def date_bills(self, subscription):
        for bill in self.datebills[subscription._login]:
            bill.id = subscription.id + '.' + bill.id
            yield bill

    def get_renew_date(self, subscription):
        login = subscription._login
        div = self.document.xpath('//div[@login="%s"]' % login)[0]
        mydate = div.xpath('.//span[@class="actif"]')[0].text
        mydate = date(*reversed([int(x) for x in mydate.split("/")]))
        if mydate.month == 12:
            mydate = mydate.replace(month=1)
            mydate = mydate.replace(year=mydate.year + 1)
        else:
            try:
                mydate = mydate.replace(month=mydate.month + 1)
            except ValueError:
                lastday = calendar.monthrange(mydate.year, mydate.month + 1)[1]
                mydate = mydate.replace(month=mydate.month + 1, day=lastday)
        return mydate


def _get_date(detail):
    return detail.datetime


class HistoryPage(BasePage):

    def on_loaded(self):
        self.calls = []
        for tr in self.document.xpath('//tr'):
            tds = tr.xpath('td')
            if tds[0].text is None or tds[0].text == "Date":
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

    def get_calls(self):
        return sorted(self.calls, key=_get_date, reverse=True)
