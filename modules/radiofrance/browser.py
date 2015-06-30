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
from .pages import PlayerPage, JsonPage

__all__ = ['RadioFranceBrowser']


class RadioFranceBrowser(PagesBrowser):
    json_page = URL('sites/default/files/(?P<json_url>.*).json',
                    'player-json/reecoute/(?P<json_url_fip>.*)', JsonPage)
    player_page = URL('(?P<player>.*)', PlayerPage)

    def get_radio_url(self, radio, player):
        self.BASEURL = 'http://www.%s.fr/' % radio
        return self.player_page.go(player=player).get_url()

    def get_current(self, radio, json_url):
        self.BASEURL = 'http://www.%s.fr/' % radio
        return self.json_page.go(json_url=json_url).get_current()

    def get_selection(self, radio_url, json_url, radio_id):
        self.BASEURL = 'http://www.%s.fr/' % radio_url
        if radio_id == 'fipradio':
            return self.json_page.go(json_url_fip=json_url).get_selection(radio_id=radio_id)

        return self.json_page.go(json_url=json_url).get_selection(radio_id=radio_id)

    def get_audio(self, _id, radio_url, json_url, radio_id):
        for item in self.get_selection(radio_url, json_url, radio_id):
            if item.id == _id:
                return item
        return []

    def search_audio(self, pattern, radio_url, json_url, radio_id):
        for item in self.get_selection(radio_url, json_url, radio_id):
            if pattern.upper() in item.title.upper():
                yield item
