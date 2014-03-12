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

from datetime import time, datetime
from .calendar import HybrideCalendarEvent

import weboob.tools.date as date_util
import re

from weboob.tools.browser2.page import HTMLPage, method, ItemElement, SkipItem, ListElement
from weboob.tools.browser2.filters import Filter, Link, CleanText, Env


__all__ = ['ProgramPage', 'EventPage']


def format_date(date):
    splitted_date = date.split(',')[1]
    if splitted_date:
        return date_util.parse_french_date(splitted_date)


class Date(Filter):
    def filter(self, text):
        return format_date(text)


class CombineDate(Filter):
    def filter(sel, text):
        return datetime.combine(format_date(text), time.max)


class ProgramPage(HTMLPage):

    date_from = None
    date_to = None
    city = None
    categories = None

    def set_filters(self, date_from, date_to, city, categories):
        self.date_from = date_from
        self.date_to = date_to
        self.city = city
        self.categories = categories

    @method
    class list_events(ListElement):
        item_xpath = '//div[@class="catItemView groupLeading"]'

        class item(ItemElement):
            klass = HybrideCalendarEvent

            def condition(self):
                return self.check_date() and self.check_city() and self.check_category()

            def check_date(self):
                date = self.el.xpath("div[@class='catItemHeader']/span[@class='catItemDateCreated']")[0]
                event_date = format_date(date.text)
                if self.page.date_from and event_date >= self.page.date_from:
                    if not self.page.date_to:
                        return True
                    else:
                        if event_date <= self.page.date_to:
                            return True
                return False

            def check_city(self):
                return  (not self.page.city or (self.page.city and
                                                self.page.city.upper() == HybrideCalendarEvent.get_city().upper())
                        )

            def check_category(self):
                return  (not self.page.categories or HybrideCalendarEvent.get_category() in self.page.categories)

            class CheckId(Filter):
                def filter(self, a_id):
                    re_id = re.compile('/programme/item/(.*?).html', re.DOTALL)
                    _id = re_id.search(a_id).group(1)
                    if _id:
                        return _id
                    raise SkipItem()

            obj_id = CheckId(Link('div[@class="catItemHeader"]/h3[@class="catItemTitle"]/a'))
            obj_start_date = Date(CleanText('div[@class="catItemHeader"]/span[@class="catItemDateCreated"]'))
            obj_end_date = CombineDate(CleanText('div[@class="catItemHeader"]/span[@class="catItemDateCreated"]'))
            obj_summary = CleanText('div[@class="catItemHeader"]/h3[@class="catItemTitle"]/a')
            obj_city = HybrideCalendarEvent.get_city()
            obj_category = HybrideCalendarEvent.get_category()


class EventPage(HTMLPage):

    @method
    class get_event(ItemElement):
        klass = HybrideCalendarEvent

        def parse(self, el):
            div = el.xpath("//div[@class='itemView']")[0]

            if self.obj.id:
                event = self.obj
                event.url = self.page.url
                event.description = self.get_description(div)
                raise SkipItem()

            re_id = re.compile('http://www.lhybride.org/programme/item/(.*?)', re.DOTALL)
            self.env['id'] = re_id.search(self.page.url).group(1)
            self.env['url'] = self.page.url
            self.env['description'] = self.get_description(div)

        def get_description(self, div):
            description = ''

            description_intro = div.xpath("div[@class='itemBody']/div[@class='itemIntroText']/table/tbody/tr/td")

            if description_intro and len(description_intro) > 0:
                description += u'%s' % description_intro[0].text_content()

            description_content = div.xpath("div[@class='itemBody']/div[@class='itemFullText']/table/tbody/tr/td")

            if description_content and len(description_content) > 0:
                description += u'%s' % description_content[0].text_content()

            return u'%s' % description

        obj_id = Env('id')
        base = '//div[@class="itemView"]/div[@class="itemHeader"]'
        obj_start_date = Date(CleanText('%s/span[@class="itemDateCreated"]' % base))
        obj_end_date = CombineDate(CleanText('%s/span[@class="itemDateCreated"]' % base))
        obj_summary = CleanText('%s/h2[@class="itemTitle"]' % base)
        obj_city = HybrideCalendarEvent.get_city()
        obj_category = HybrideCalendarEvent.get_category()
        obj_url = Env('url')
        obj_description = Env('description')
