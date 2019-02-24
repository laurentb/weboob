# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

import re
from datetime import datetime

from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.html import AbsoluteLink
from weboob.browser.filters.standard import CleanText, Env, Field, Format
from weboob.browser.pages import HTMLPage, pagination
from weboob.capabilities.base import StringField
from weboob.capabilities.calendar import BaseCalendarEvent, CATEGORIES


LABEL_TO_CAT = {
    'Cinéma': CATEGORIES.CINE,
    'Concerts': CATEGORIES.CONCERT,
    'Conférence': CATEGORIES.CONF,
    'Expos ': CATEGORIES.EXPO,
    'Spectacles': CATEGORIES.SPECTACLE,
    'Sport': CATEGORIES.SPORT,
    'Théâtre': CATEGORIES.THEATRE,
}


CAT_TO_LABEL = {v: k for k, v in LABEL_TO_CAT.items()}


FRENCH_DAYS = ['lundi' ,'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']


class BREvent(BaseCalendarEvent):
    siteid = StringField('Site id')


class SearchPage(HTMLPage):
    def search(self, q):
        form = self.get_form(name='form1')
        form['titre'] = q.summary or ''
        form['cp'] = q.city or ''
        form['tri'] = 'date'
        form['jj'] = q.start_date.strftime('%d')
        form['dt'] = q.start_date.strftime('%Y-%m')

        form['idrub'] = []
        for cat in q.categories:
            if cat not in CAT_TO_LABEL:
                continue
            for id in self.doc.xpath('//label[@class="lrubr1"][contains(text(),$txt)]/input/@value', txt=CAT_TO_LABEL[cat]):
                form['idrub'].append(id)
                break
        assert form['idrub']

        form.submit()


class TimeParser(object):
    # phrasing can be: "du lundi au samedi à 16h et le lundi et le dimanche à 15h30, dimanche, mardi à 12h, 13h et 14h"
    def __init__(self, txt, weekday):
        self.weekday = weekday

        txt = re.sub(r'\ble\s+|\s+et\s+|,', ' ', txt)
        txt = re.sub(r'\s\s+', ' ', txt).strip()

        self.parts = txt.split()
        self.res = []
        self.days = []

    def do_parse(self):
        for i in self.parts:
            self.parse(i)

    def parse_start(self, i):
        if i == 'du':
            self.parse = self.parse_range
        else:
            self.days.append(FRENCH_DAYS.index(i))
            self.parse = self.parse_after_day

    def parse_range(self, i):
        self.rstart = FRENCH_DAYS.index(i)
        self.parse = self.parse_to

    def parse_to(self, i):
        assert i == 'au'
        self.parse = self.parse_to2

    def parse_to2(self, i):
        self.rend = FRENCH_DAYS.index(i)
        self.days.extend(range(self.rstart, self.rend + 1))
        self.parse = self.parse_after_day

    def parse_after_day(self, i):
        if i == 'à':
            self.parse = self.parse_time
        else:
            self.parse_start(i)

    time_re = re.compile(r'(\d+)h(\d*)$')

    def parse_time(self, i):
        m = self.time_re.match(i)
        if self.weekday in self.days:
            self.res.append((int(m.group(1)), int(m.group(2) or 0)))

        self.parse = self.parse_after_time

    def parse_after_time(self, i):
        if self.time_re.match(i):
            self.parse_time(i)
        else:
            self.days = []
            self.parse = self.parse_start
            self.parse(i)

    parse = parse_start


class ResultsPage(HTMLPage):
    @pagination
    @method
    class iter_events(ListElement):
        item_xpath = '//table[@id="preliste"]/tr'
        next_page = AbsoluteLink('(//a[text()=">"][contains(@href,"LISTEPEpg")])[1]')

        class item(ItemElement):
            klass = BREvent

            obj_summary = CleanText('.//h4')
            obj_url = AbsoluteLink('.//h4/a')
            obj_description = CleanText('.//div[@class="libellepreliste"]')
            obj_city = CleanText('(.//span[@class="lieu"]/a)[2]')
            obj_location = CleanText('(.//span[@class="lieu"]/a)[1]')
            obj_timezone = 'Europe/Paris'

            def obj_price(self):
                return float(CleanText('.//span[@class="prixli"]')(self).replace('€', '.'))

            def obj__date_hours(self):
                date = Env('date')(self)
                weekday = date.weekday()

                txt = CleanText('.//p[@class="sb"]')(self).lower()
                m = re.match(r'du \d+/\d+/\d+ au \d+/\d+/\d+ (.*)', txt)
                if m:
                    txt = m.group(1)
                    p = TimeParser(txt, weekday)
                    p.do_parse()
                    return p.res

                m = re.match('le \w+ \d+ \w+ \d+ à (\d+)h(\d*)$', txt, re.UNICODE)
                return [(int(m.group(1)), int(m.group(2) or 0))]

            obj_start_date = Env('date')

            def obj_category(self):
                text = CleanText('.//h4/following-sibling::span[@class="small"]/a')(self)
                for k in LABEL_TO_CAT:
                    if k in text:
                        return LABEL_TO_CAT[k]
                return CATEGORIES.AUTRE

            def obj_siteid(self):
                return self.page.browser.event.match(Field('url')(self)).group('id')


class EventPage(HTMLPage):
    @method
    class get_event(ItemElement):
        klass = BREvent

        def obj_url(self):
            return self.page.url

        obj_summary = CleanText('//div[@class="evtTitre"]/h2')
        obj_description = Format('%s\n%s', CleanText('//h6[@itemprop]'), CleanText('//div[@id="speDescription"]'))

        obj_location = CleanText('//td[@class="colLeftSeparator"]//a[starts-with(@href,"/lieu/")]')
        obj_city = CleanText('//td[@class="colLeftSeparator"]//a[starts-with(@href,"/spectacle-")]')
        obj_timezone = 'Europe/Paris'

        def obj_siteid(self):
            return self.page.browser.event.match(Field('url')(self)).group('id')

        def obj_category(self):
            text = CleanText('//div[@id="contextchemin"]')(self)
            for k in LABEL_TO_CAT:
                if k in text:
                    return LABEL_TO_CAT[k]
            return CATEGORIES.AUTRE


class EventDatesPage(HTMLPage):
    def fetch_by_date(self, event, ymd, hm):
        book = self.browser.book.build(id=event.siteid, ymd=ymd, hm=hm)
        book = book.replace(self.browser.BASEURL, '')
        for a in self.doc.xpath('//a[@href = $url]', url=book):
            event.price = self.parse_price(a)
            return

    def parse_price(self, a):
        return float(re.search(r'\d+€\d*', a.attrib['title']).group(0).replace('€', '.'))

    def get_first(self, event):
        prefix = '/evtBook.htm?idevt=%s' % event.siteid
        for a in self.doc.xpath('//a[starts-with(@href, $pfx)]', pfx=prefix):
            bookurl = self.browser.absurl(a.attrib['href'], base=True)
            d = self.browser.book.match(bookurl).groupdict()
            s = '%sT%s' % (d['ymd'], d['hm'])
            event.start_date = datetime.strptime(s, '%Y-%m-%dT%H:%M')
            event.price = self.parse_price(a)
            return
