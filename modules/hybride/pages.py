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
from weboob.tools.browser import BasePage
from .calendar import HybrideCalendarEvent
import weboob.tools.date as date_util
import re

__all__ = ['ProgramPage', 'EventPage']


def format_date(date):
    splitted_date = date.split(',')[1]
    if splitted_date:
        return date_util.parse_french_date(splitted_date)


class ProgramPage(BasePage):
    def list_events(self, date_from, date_to=None, city=None, categories=None):
        divs = self.document.getroot().xpath("//div[@class='catItemView groupLeading']")
        for div in divs:
            if(self.is_event_in_valid_period(div, date_from, date_to)):
                event = self.create_event(div, city, categories)
                if event:
                    yield event

    def create_event(self, div, city=None, categories=None):
        re_id = re.compile('/programme/item/(.*?).html', re.DOTALL)
        header = self.parser.select(div, "div[@class='catItemHeader']", 1, method='xpath')
        date = self.parser.select(header, "span[@class='catItemDateCreated']", 1, method='xpath')
        a_id = self.parser.select(header, "h3[@class='catItemTitle']/a", 1, method='xpath')
        _id = re_id.search(a_id.attrib['href']).group(1)
        if _id:
            event = HybrideCalendarEvent(_id)
            event.start_date = format_date(date.text)
            event.end_date = datetime.combine(event.start_date, time.max)
            event.summary = u'%s' % a_id.text_content().strip()
            if self.is_valid_event(event, city, categories):
                return event

    def is_valid_event(self, event, city, categories):
        if city and city != '' and city.upper() != event.city.upper():
            return False

        if categories and len(categories) > 0 and event.category not in categories:
            return False

        return True

    def is_event_in_valid_period(self, div, date_from, date_to=None):
        header = self.parser.select(div, "div[@class='catItemHeader']", 1, method='xpath')
        date = self.parser.select(header, "span[@class='catItemDateCreated']", 1, method='xpath')
        event_date = format_date(date.text)
        if event_date > date_from:
            if not date_to:
                return True
            else:
                if event_date < date_to:
                    return True
        return False


class EventPage(BasePage):
    def get_event(self, url, event=None):
        if not event:
            re_id = re.compile('http://www.lhybride.org/programme/item/(.*?).html', re.DOTALL)
            event = HybrideCalendarEvent(re_id.search(url).group(1))

        event.url = url

        div = self.document.getroot().xpath("//div[@class='itemView']")[0]
        header = self.parser.select(div, "div[@class='itemHeader']", 1, method='xpath')

        date = self.parser.select(header, "span[@class='itemDateCreated']", 1, method='xpath')
        event.start_date = format_date(date.text)
        event.end_date = datetime.combine(event.start_date, time.max)

        summary = self.parser.select(header, "h2[@class='itemTitle']", 1, method='xpath')
        event.summary = u'%s' % summary.text_content().strip()

        description = ''

        description_intro = self.parser.select(div, "div[@class='itemBody']/div[@class='itemIntroText']/table/tbody/tr/td",
                                               method='xpath')
        if description_intro and len(description_intro) > 0:
            description += u'%s' % description_intro[0].text_content()

        description_content = self.parser.select(div, "div[@class='itemBody']/div[@class='itemFullText']/table/tbody/tr/td",
                                                 method='xpath')
        if description_content and len(description_content) > 0:
            description += u'%s' % description_content[0].text_content()

        event.description = u'%s' % description
        return event
