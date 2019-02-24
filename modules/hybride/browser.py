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

from .pages import ProgramPage, EventPage

from weboob.browser import PagesBrowser, URL
from weboob.browser.profiles import Firefox

__all__ = ['HybrideBrowser']


class HybrideBrowser(PagesBrowser):
    PROFILE = Firefox()
    BASEURL = 'http://www.lhybride.org/'

    program_page = URL('programmation/a-venir.html', ProgramPage)
    event_page = URL('programmation/item/(?P<_id>.*)', EventPage)

    def list_events(self, date_from, date_to=None, city=None, categories=None):
        return self.program_page.go().list_events(date_from=date_from,
                                                  date_to=date_to,
                                                  city=city,
                                                  categories=categories)

    def get_event(self, _id, event=None):
        return self.event_page.go(_id=_id).get_event(obj=event)
