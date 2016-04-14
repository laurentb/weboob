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
from .pages import RadioPage, JsonPage, PodcastPage

__all__ = ['RadioFranceBrowser']


class RadioFranceBrowser(PagesBrowser):
    json_page = URL('sites/default/files/(?P<json_url>.*).json',
                    'player-json/reecoute/(?P<json_url_fip>.*)',
                    'station/(?P<fbplayer>.*)',
                    'programmes\?xmlHttpRequest=1',
                    'autocomplete/emissions.json',
                    JsonPage)
    podcast_page = URL('podcast09/rss_(?P<podcast_id>.*)\.xml', PodcastPage)
    radio_page = URL('(?P<page>.*)', RadioPage)

    def get_radio_url(self, radio, player):
        if radio == 'francebleu':
            self.BASEURL = 'https://www.%s.fr/' % radio
            return self.json_page.go(fbplayer=player).get_fburl()

        self.BASEURL = 'http://www.%s.fr/' % radio
        if radio == 'franceculture':
            self.location('%s%s' % (self.BASEURL, player))
            return self.page.get_france_culture_url()

        return self.radio_page.go(page=player).get_url()

    def get_current(self, radio, url):
        if radio == 'francebleu':
            self.BASEURL = 'https://www.%s.fr/' % radio
            return self.radio_page.go(page=url).get_current()

        self.BASEURL = 'http://www.%s.fr/' % radio
        if radio == 'franceculture':
            return self.json_page.go().get_france_culture_current()

        return self.json_page.go(json_url=url).get_current()

    def get_selection(self, radio_url, json_url, radio_id):
        self.BASEURL = 'http://www.%s.fr/' % radio_url
        if radio_id == 'fipradio':
            return self.json_page.go(json_url_fip=json_url).get_selection(radio_id=radio_id)
        elif radio_id == 'franceculture':
            return self.radio_page.go(page='').get_france_culture_selection(radio_id=radio_id)

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

    def get_podcast_emissions(self, radio_url, podcast_url, split_path):
        self.BASEURL = 'http://www.%s.fr/' % radio_url
        if split_path[0] == 'franceinter':
            return self.radio_page.go(page=podcast_url).get_france_inter_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'franceculture':
            self.location('%s%s' % (self.BASEURL, podcast_url))
            return self.page.get_france_culture_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'franceinfo':
            return self.radio_page.go(page=podcast_url).get_france_info_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'francemusique':
            return self.radio_page.go(page=podcast_url).get_france_musique_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'mouv':
            return self.radio_page.go(page=podcast_url).get_mouv_podcast_emissions(split_path=split_path)

    def get_podcasts(self, podcast_id):
        self.BASEURL = 'http://radiofrance-podcast.net/'
        return self.podcast_page.go(podcast_id=podcast_id).iter_podcasts()

    def get_france_culture_podcasts_url(self, url):
        self.BASEURL = 'http://www.franceculture.fr/'
        return self.radio_page.go(page='emissions/%s' % url).get_france_culture_podcasts_url()
