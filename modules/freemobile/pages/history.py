# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Florent Fourcot
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


import calendar
from datetime import datetime
from decimal import Decimal

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Date, CleanText, Filter,\
    CleanDecimal, Currency, Regexp, Field, DateTime, Format, Env
from weboob.browser.filters.html import AbsoluteLink, Attr
from weboob.capabilities.bill import DocumentTypes, Detail, Bill
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import ParseError
from weboob.tools.compat import unicode


class FormatDate(Filter):
    def filter(self, txt):
        return datetime.strptime(txt, "%Y%m%d").date()


class BadUTF8Page(HTMLPage):
    ENCODING = 'UTF-8'


class DetailsPage(LoggedPage, BadUTF8Page):
    def load_virtual(self, phonenumber):
        for div in self.doc.xpath('//div[@class="infosLigne pointer"]'):
            if CleanText('.')(div).split("-")[-1].strip() == phonenumber:
                return Attr('.', 'onclick')(div).split('(')[1][1]

    def on_load(self):
        self.details = {}
        for div in self.doc.xpath('//div[@class="infosConso"]'):
            num = div.attrib['id'].split('_')[1][0]
            self.details[num] = []

            # National parsing
            divnat = div.xpath('div[@class="national"]')
            if divnat:
                divnat = divnat[0]
                self._parse_div(divnat, "National : %s | International : %s", num, False)

            # International parsing
            divint = div.xpath('div[@class="international hide"]')
            if divint:
                divint = divint[0]
                if divint.xpath('div[@class="detail"]'):
                    self._parse_div(divint, u"Appels émis : %s | Appels reçus : %s", num, True)

    def _parse_div(self, divglobal, string, num, inter=False):
        divs = divglobal.xpath('div[@class="detail"]')
        # Two pieces of information in one div...
        div = divs.pop(0)
        voice = self._parse_voice(div, string, num, inter)
        self.details[num].append(voice)
        self._iter_divs(divs, num, inter)

    def _iter_divs(self, divs, num, inter=False):
        for div in divs:
            detail = Detail()
            detail.label = CleanText('div[@class="titre"]/p')(div)
            detail.id = "-" + detail.label.split(' ')[1].lower()
            if inter:
                detail.label = detail.label + u" (international)"
                detail.id = detail.id + "-inter"
            detail.infos = CleanText('div[@class="conso"]/p')(div)
            detail.price = CleanDecimal('div[@class="horsForfait"]/p/span', default=Decimal(0), replace_dots=True)(div)
            detail.currency = Currency('div[@class="horsForfait"]/p/span')(div)

            self.details[num].append(detail)

    def _parse_voice(self, div, string, num, inter=False):
        voicediv = div.xpath('div[@class="conso"]')[0]
        voice = Detail()
        voice.id = "-voice"
        voice.label = CleanText('div[@class="titre"]/p')(div)
        if inter:
            voice.label = voice.label + " (international)"
            voice.id = voice.id + "-inter"
        voice.price = CleanDecimal('div[@class="horsForfait"]/p/span', default=Decimal(0), replace_dots=True)(div)
        voice.currency = Currency('div[@class="horsForfait"]/p/span')(div)
        voice1 = CleanText('.//span[@class="actif"][1]')(voicediv)
        voice2 = CleanText('.//span[@class="actif"][2]')(voicediv)
        voice.infos = unicode(string) % (voice1, voice2)

        return voice

    # XXX
    def get_details(self, subscription):
        for detail in self.details[subscription._virtual]:
            detail.id = subscription.id + detail.id
            yield detail

    @method
    class date_bills(ListElement):
        item_xpath = '//div[has-class("factLigne")]'

        class item(ItemElement):
            klass = Bill

            def condition(self):
                num = Attr('.', 'data-fact_ligne', default='')(self)
                return self.env['subid'] == num

            obj_url = AbsoluteLink('.//div[@class="pdf"]/a')
            obj__localid = Regexp(Field('url'), '&id=(.*)&date', u'\\1')
            obj_label = Regexp(Field('url'), '&date=(\d*)', u'\\1')
            obj_id = Format('%s.%s', Env('subid'), Field('_localid'))
            obj_date = FormatDate(Field('label'))
            obj_format = u"pdf"
            obj_type = DocumentTypes.BILL
            obj_price = CleanDecimal('div[@class="montant"]', default=Decimal(0), replace_dots=False)
            obj_currency = Currency('div[@class="montant"]')

    def get_renew_date(self, subscription):
        div = self.doc.xpath('//div[@login=$login]', login=subscription._login)[0]

        try:
            mydate = Date(CleanText('.//div[@class="resumeConso"]/span[@class="actif"][1]'), dayfirst=True)(div)
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
        except ParseError:
            return NotAvailable

    def get_login(self, phonenumber):
        return Attr('.', 'login')(self.doc.xpath('//div[div[contains(text(), $phone)]]', phone=phonenumber)[0])

class HistoryPage(LoggedPage, BadUTF8Page):
    @method
    class get_calls(ListElement):
        item_xpath = '//tr'

        class item(ItemElement):
            klass = Detail

            def condition(self):
                txt = self.el.xpath('td[1]')[0].text
                return (txt is not None) and (txt != "Date")

            obj_id = None
            obj_datetime = DateTime(CleanText('td[1]', symbols=u'à'), dayfirst=True)
            obj_label = Format(u'%s %s %s', CleanText('td[3]'), CleanText('td[2]'),
                               CleanText('td[4]'))
            obj_price = CleanDecimal('td[5]', default=Decimal(0), replace_dots=True)
            obj_currency = Currency('td[5]')
