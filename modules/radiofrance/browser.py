# * -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Johann Broudin, Laurent Bachelier
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
        self.fill_base_url(radio)

        if radio == 'francebleu':
            return self.json_page.go(fbplayer=player).get_fburl()

        return self.radio_page.go(page=player).get_url()

    def fill_base_url(self, radio):
        if radio in ['franceinter', 'francebleu', 'franceculture', 'francemusique']:
            self.BASEURL = 'https://www.%s.fr/' % radio
        else:
            self.BASEURL = 'http://www.%s.fr/' % radio

    def get_current(self, radio, url):
        self.fill_base_url(radio)

        if radio == 'francebleu':
            return self.radio_page.go(page=url).get_current()

        if radio in ['franceculture', 'franceinter', 'francemusique']:
            return self.json_page.go().get_culture_inter_current()

        if radio == 'francetvinfo':
            return u'', u''

        return self.json_page.go(json_url=url).get_current()

    def get_selection(self, radio_url, json_url, radio_id):
        self.BASEURL = 'http://www.%s.fr/' % radio_url
        if radio_id == 'fipradio':
            return self.json_page.go(json_url_fip=json_url).get_selection(radio_id=radio_id)
        elif radio_id == 'franceculture':
            self.fill_base_url(radio_id)
            return self.radio_page.go(page='').get_france_culture_selection(radio_id=radio_id)
        elif radio_id == 'francetvinfo':
            self.fill_base_url(radio_id)
            selection_list = self.radio_page.go(page=json_url).get_francetvinfo_selection_list()
            sel = []
            for item in selection_list:
                sel.append(self.radio_page.go(page=item).get_francetvinfo_selection())
            return sel

        return self.json_page.go(json_url=json_url).get_selection(radio_id=radio_id)

    def get_audio(self, _id, radio_url, json_url, radio_id):
        for item in self.get_selection(radio_url, json_url, radio_id):
            if item.id == _id:
                return item
        return []

    def get_podcast_emissions(self, radio_url, podcast_url, split_path):
        self.fill_base_url(radio_url)
        if split_path[0] == 'franceinter':
            return self.radio_page.go(page=podcast_url).get_france_inter_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'franceculture':
            self.location('%s%s' % (self.BASEURL, podcast_url))
            return self.page.get_france_culture_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'francetvinfo':
            return self.radio_page.go(page=podcast_url).get_france_info_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'francemusique':
            return self.radio_page.go(page=podcast_url).get_france_musique_podcast_emissions(split_path=split_path)
        elif split_path[0] == 'mouv':
            return self.radio_page.go(page=podcast_url).get_mouv_podcast_emissions(split_path=split_path)

    def get_podcasts(self, podcast_id):
        self.BASEURL = 'http://radiofrance-podcast.net/'
        return self.podcast_page.go(podcast_id=podcast_id).iter_podcasts()

    def get_france_culture_podcasts_url(self, url):
        self.BASEURL = 'https://www.franceculture.fr/'
        return self.radio_page.go(page='emissions/%s' % url).get_france_culture_podcasts_url()

    def get_francetvinfo_podcasts_url(self, url):
        self.BASEURL = 'http://www.francetvinfo.fr/'
        return self.radio_page.go(page='replay-radio/%s' % url).get_francetvinfo_podcasts_url()
