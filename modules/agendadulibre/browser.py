# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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


from weboob.browser import PagesBrowser, URL

from .pages import EventListPage, EventPage
from datetime import timedelta, date


class AgendadulibreBrowser(PagesBrowser):

    event_list_page = URL('events\?start_date=(?P<date_from>.*)(?P<region>.*)', EventListPage)
    event_page = URL('events/(?P<_id>.*)', EventPage)

    def __init__(self, website, region, *args, **kwargs):
        self.BASEURL = u'%s/' % website
        self.region = '&region=%s' % region if region else ''
        PagesBrowser.__init__(self, *args, **kwargs)

    def list_events(self, date_from, date_to, city=None, categories=None, max_date=None):
        _max_date = date_from + timedelta(days=365)
        max_date = date(year=_max_date.year, month=_max_date.month, day=_max_date.day)
        return self.event_list_page.go(date_from=date_from.strftime("%Y-%m-%d"),
                                       region=self.region)\
            .list_events(date_from=date_from,
                         date_to=date_to,
                         city=city,
                         categories=categories,
                         max_date=max_date)

    def get_event(self, event_id, event=None):
        _id = event_id.split('#')[-1]
        return self.event_page.go(_id=_id).get_event(obj=event)
