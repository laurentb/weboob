# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from datetime import datetime, time

import weboob.tools.date as date_util
from .calendar import BiplanCalendarEventConcert, BiplanCalendarEventTheatre

from weboob.browser.elements import ItemElement, SkipItem, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import Filter, CleanText, Env, Regexp, CombineDate
from weboob.browser.filters.html import Link, CleanHTML


class BiplanPrice(Filter):
    def filter(self, el):
        index = 1 if len(el) > 1 else 0
        content = CleanText.clean(CleanText('.', ['HORAIRES'])(el[index]))
        a_price = content.split(' - ')[-1]
        parsed_price = re.findall(r"\d*\,\d+|\d+", " ".join(a_price))

        if parsed_price and len(parsed_price) > 0:
            return float(parsed_price[0].replace(',', '.'))

        return float(0)


class BiplanDate(Filter):
    def filter(self, el):
        content = CleanText.clean(CleanText(CleanHTML('.'), ['*'])(el[0]))
        a_date = content[0:content.index(' - ')]

        for fr, en in date_util.DATE_TRANSLATE_FR:
            a_date = fr.sub(en, a_date)

        try:
            _month = datetime.strptime(a_date, "%A %d %B").month
            if (datetime.now().month > _month):
                a_date += u' %i' % (datetime.now().year + 1)
            else:
                a_date += u' %i' % (datetime.now().year)
        except ValueError:
            pass

        return datetime.strptime(a_date, "%A %d %B %Y")


class StartTime(Filter):
    def filter(self, el):
        index = 1 if len(el) > 1 else 0
        content = CleanText.clean(CleanText('.', ['HORAIRES'])(el[index]))
        _content = content.split(' - ')
        a_time = _content[2] if len(_content) > 2 else _content[0]
        regexp = re.compile(r'(?P<hh>\d+)h?(?P<mm>\d+)')
        m = regexp.search(a_time)
        if m:
            return time(int(m.groupdict()['hh'] or 0), int(m.groupdict()['mm'] or 0))
        return time(0, 0)


class EndTime(Filter):
    def filter(self, el):
        return time.max


class ProgramPage(HTMLPage):

    @method
    class list_events(ListElement):
        item_xpath = '//div[@class="ligne"]'

        class item(ItemElement):
            def klass(self):
                return BiplanCalendarEventConcert() if self.env['is_concert'] else BiplanCalendarEventTheatre()

            def condition(self):
                return (self.el.xpath('./div') and CleanText('./div/a/img/@src')(self)[-1] != '/')

            def validate(self, obj):
                return (self.is_valid_event(obj, self.env['city'], self.env['categories']) and
                        self.is_event_in_valid_period(obj.start_date, self.env['date_from'], self.env['date_to']))

            def is_valid_event(self, event, city, categories):
                if city and city != '' and city.upper() != event.city.upper():
                    return False

                if categories and len(categories) > 0 and event.category not in categories:
                    return False

                return True

            def is_event_in_valid_period(self, event_date, date_from, date_to):
                if event_date >= date_from:
                    if not date_to:
                        return True
                    else:
                        if event_date <= date_to:
                            return True
                return False

            obj_id = Regexp(Link('./div/a'), '/(.*?).html')
            obj_start_date = CombineDate(BiplanDate('div/div/b'), StartTime('div/div/b'))
            obj_end_date = CombineDate(BiplanDate('div/div/b'), EndTime('.'))
            obj_price = BiplanPrice('div/div/b')
            obj_summary = CleanText("div/div/div/a/strong")


class EventPage(HTMLPage):

    encoding = u'utf-8'

    @method
    class get_event(ItemElement):
        klass = BiplanCalendarEventConcert if Env('is_concert') else BiplanCalendarEventTheatre

        def parse(self, el):
            _div = "//div/div/div[@id='popup']"
            div = el.xpath("%s" % _div)[0]
            if self.obj.id:
                event = self.obj
                event.url = self.page.url
                event.description = CleanHTML("%s/div/div[@class='presentation-popup']" % _div)(self)
                raise SkipItem()

            self.env['is_concert'] = (div.attrib['class'] != 'theatre-popup')
            self.env['url'] = self.page.url

        obj_id = Env('_id')
        base = "//div[@id='popup']"
        obj_price = BiplanPrice("%s/div/b" % base)
        obj_start_date = CombineDate(BiplanDate("%s/div/b" % base), StartTime("%s/div/b" % base))
        obj_end_date = CombineDate(BiplanDate("%s/div/b" % base), EndTime("."))
        obj_url = Env('url')
        obj_summary = CleanText('%s/div/div/span' % base)
        obj_description = CleanHTML('%s/div/div[@class="presentation-popup"]' % base)
