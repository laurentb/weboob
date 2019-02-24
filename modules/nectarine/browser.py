# * -*- coding: utf-8 -*-

# Copyright(C) 2013  Thomas Lecavelier
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
from .pages import LivePage, StreamsPage

__all__ = ['NectarineBrowser']


class NectarineBrowser(PagesBrowser):
    BASEURL = 'https://www.scenemusic.net'

    streams = URL(r'/demovibes/xml/streams/', StreamsPage)
    live = URL(r'/demovibes/xml/queue/', LivePage)

    def home(self):
        self.location('/demovibes/xml/streams/')

        assert self.streams.is_here()

    def iter_radios_list(self):
        self.location('/demovibes/xml/streams/')

        assert self.streams.is_here()
        return self.page.iter_radios_list()

    def get_current_emission(self):
        self.location('/demovibes/xml/queue/')
        assert self.live.is_here()
        return self.page.get_current_emission()
