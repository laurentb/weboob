# * -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Johann Broudin, Laurent Bachelier
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
from .pages import PlayerPage, TimelinePage

__all__ = ['RadioFranceBrowser']


class RadioFranceBrowser(PagesBrowser):
    timeline = URL('sites/default/files/(?P<json_url>.*).json', TimelinePage)
    player_page = URL('(?P<player>.*)', PlayerPage)

    def get_radio_url(self, radio, player):
        self.BASEURL = 'http://www.%s.fr/' % radio
        return self.player_page.go(player=player).get_url()

    def get_current(self, radio, json_url):
        self.BASEURL = 'http://www.%s.fr/' % radio
        return self.timeline.go(json_url=json_url).get_current()
