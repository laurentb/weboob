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

from weboob.tools.browser.decorators import id2url
from weboob.tools.browser import BaseBrowser
from .calendar import HybrideCalendarEvent
from .pages import ProgramPage, EventPage


__all__ = ['HybrideBrowser']


class HybrideBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.lhybride.org'
    ENCODING = None

    PAGES = {
        '%s://%s/programme.html' % (PROTOCOL, DOMAIN): ProgramPage,
        '%s://%s/programme/item/(.*?)' % (PROTOCOL, DOMAIN): EventPage,
    }

    def list_events(self, date_from, date_to=None, city=None, categories=None):
        self.location('%s://%s/programme.html' % (self.PROTOCOL, self.DOMAIN))
        assert self.is_on_page(ProgramPage)
        return self.page.list_events(date_from, date_to, city, categories)

    @id2url(HybrideCalendarEvent.id2url)
    def get_event(self, url, event=None):
        self.location(url)
        assert self.is_on_page(EventPage)
        return self.page.get_event(url, event)
