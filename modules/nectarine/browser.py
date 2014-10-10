# * -*- coding: utf-8 -*-

# Copyright(C) 2013  Thomas Lecavelier
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

from weboob.deprecated.browser import Browser
from .pages import LivePage, StreamsPage

__all__ = ['NectarineBrowser']


class NectarineBrowser(Browser):
    DOMAIN = 'www.scenemusic.net'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['desktop_firefox']
    PAGES = {
        'https://www\.scenemusic\.net/demovibes/xml/streams/': StreamsPage,
        'https://www\.scenemusic\.net/demovibes/xml/queue/': LivePage
    }

    def home(self):
        self.location('/demovibes/xml/streams/')

        assert self.is_on_page(StreamsPage)

    def iter_radios_list(self):
        self.location('/demovibes/xml/streams/')

        assert self.is_on_page(StreamsPage)
        return self.page.iter_radios_list()

    def get_current_emission(self):
        self.location('/demovibes/xml/queue/')
        assert self.is_on_page(LivePage)
        return self.page.get_current_emission()
