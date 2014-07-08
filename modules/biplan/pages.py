# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from datetime import datetime, time

import weboob.tools.date as date_util
from .calendar import BiplanCalendarEventConcert, BiplanCalendarEventTheatre

from weboob.tools.browser2.elements import ItemElement, SkipItem, ListElement
from weboob.tools.browser2.page import HTMLPage, method
from weboob.tools.browser2.filters import Filter, Link, CleanText, Env, Regexp, CombineDate, CleanHTML


__all__ = ['ProgramPage', 'EventPage']


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
        a_time = content.split(' - ')[-2]
        regexp = re.compile(ur'(?P<hh>\d+)h?(?P<mm>\d+)')
        m = regexp.search(a_time)
        return time(int(m.groupdict()['hh'] or 0), int(m.groupdict()['mm'] or 0))


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
                return (self.el.xpath('./div'))

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
