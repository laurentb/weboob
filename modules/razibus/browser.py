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


__all__ = ['RazibusBrowser']


class RazibusBrowser(PagesBrowser):
    BASEURL = 'http://razibus.net/'
    TIMEOUT = 20
    event_list_page = URL('evenements-a-venir.php\?region=(?P<region>.*)', EventListPage)
    event_page = URL('(?P<_id>.*).html', EventPage)
    region = None

    def __init__(self, region, *args, **kwargs):
        super(RazibusBrowser, self).__init__(*args, **kwargs)
        self.region = region

    def get_event(self, _id, event=None):
        return self.event_page.go(_id=_id).get_event(obj=event)

    def list_events(self, date_from, date_to, city=None, categories=None):
        return self.event_list_page.go(region=self.region).list_events(date_from=date_from,
                                                                       date_to=date_to,
                                                                       city=city,
                                                                       categories=categories)
