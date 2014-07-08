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

from weboob.tools.browser2.page import HTMLPage, method
from weboob.tools.browser2.elements import ItemElement, SkipItem, ListElement
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


class Description(Filter):
    def filter(self, el):
        description = ''

        description_intro = el[0].xpath("div[@class='itemIntroText']/table/tbody/tr/td")

        if description_intro and len(description_intro) > 0:
            description += u'%s' % description_intro[0].text_content()

        description_content = el[0].xpath("div[@class='itemFullText']/table/tbody/tr/td")

        if description_content and len(description_content) > 0:
            description += u'%s' % description_content[0].text_content()

        return u'%s' % description


class ProgramPage(HTMLPage):

    @method
    class list_events(ListElement):
        item_xpath = '//div[@class="catItemView groupLeading"]'

        class item(ItemElement):
            klass = HybrideCalendarEvent

            def validate(self, obj):
                return self.check_date(obj) and self.check_city(obj) and self.check_category(obj)

            def check_date(self, obj):
                if self.env['date_from'] and obj.start_date >= self.env['date_from']:
                    if not self.env['date_to']:
                        return True
                    else:
                        if obj.end_date <= self.env['date_to']:
                            return True
                return False

            def check_city(self, obj):
                return (not self.env['city'] or self.env['city'].upper() == obj.city.upper())

            def check_category(self, obj):
                return (not self.env['categories'] or obj.category in self.env['categories'])

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


class EventPage(HTMLPage):

    @method
    class get_event(ItemElement):
        klass = HybrideCalendarEvent

        def parse(self, el):
            if self.obj.id:
                event = self.obj
                event.url = self.page.url
                event.description = Description('//div[@class="itemView"]/div[@class="itemBody"]')(self)
                raise SkipItem()

            self.env['url'] = self.page.url

        obj_id = Env('_id')
        base = '//div[@class="itemView"]/div[@class="itemHeader"]'
        obj_start_date = Date(CleanText('%s/span[@class="itemDateCreated"]' % base))
        obj_end_date = CombineDate(CleanText('%s/span[@class="itemDateCreated"]' % base))
        obj_summary = CleanText('%s/h2[@class="itemTitle"]' % base)
        obj_url = Env('url')
        obj_description = Description('//div[@class="itemView"]/div[@class="itemBody"]')
