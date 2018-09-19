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


from weboob.browser import PagesBrowser, URL

from .pages import ProgramPage, EventPage

__all__ = ['BiplanBrowser']


class BiplanBrowser(PagesBrowser):
    BASEURL = 'https://www.lebiplan.org'

    program_page = URL('/fr/biplan-prog-(?P<_category>.*).php', ProgramPage)
    event_page = URL('/(?P<_id>.*).html', EventPage)

    def list_events_concert(self, date_from, date_to=None, city=None, categories=None):
        return self.program_page.go(_category='concert').list_events(date_from=date_from,
                                                                     date_to=date_to,
                                                                     city=city,
                                                                     categories=categories,
                                                                     is_concert=True)

    def list_events_theatre(self, date_from, date_to=None, city=None, categories=None):
        return self.program_page.go(_category='theatre').list_events(date_from=date_from,
                                                                     date_to=date_to,
                                                                     city=city,
                                                                     categories=categories,
                                                                     is_concert=False)

    def get_event(self, _id, event=None):
        return self.event_page.go(_id=_id).get_event(obj=event)
