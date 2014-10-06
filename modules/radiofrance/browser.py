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

from weboob.deprecated.browser import Browser, Page
from weboob.tools.json import json
from weboob.capabilities.video import BaseVideo
from weboob.deprecated.browser.decorators import id2url

from time import time
import re
from urlparse import parse_qs


__all__ = ['RadioFranceBrowser', 'RadioFranceVideo']


class RadioFranceVideo(BaseVideo):
    RADIO_DOMAINS = ('franceinter', 'franceculture', 'fipradio', 'franceinfo')

    def __init__(self, *args, **kwargs):
        BaseVideo.__init__(self, *args, **kwargs)
        self.ext = u'mp3'

    @classmethod
    def id2url(cls, _id):
        radio_id, replay_id = _id.split('-', 2)
        radio_domain = 'fipradio' if radio_id == 'fip' else radio_id
        return 'http://www.%s.fr/player/reecouter?play=%s' % \
            (radio_domain, replay_id)


class PlayerPage(Page):
    URL = r'^http://www\.(?P<rdomain>%s)\.fr/player/reecouter\?play=(?P<replay_id>\d+)$' \
        % '|'.join(RadioFranceVideo.RADIO_DOMAINS)
    MP3_REGEXP = re.compile(r'sites%2Fdefault.+.(?:MP3|mp3)')

    def get_url(self):
        radio_domain = self.groups[0]
        player = self.parser.select(self.document.getroot(), '#rfPlayer embed', 1)
        urlparams = parse_qs(player.attrib['src'])
        return 'http://www.%s.fr/%s' % (radio_domain, urlparams['urlAOD'][0])


class ReplayPage(Page):
    URL = r'^http://www\.(?P<rdomain>%s)\.fr/(?:emission|diffusion)-.+$' \
        % '|'.join(RadioFranceVideo.RADIO_DOMAINS)
    # the url does not always end with id-yyy-mm-dd, sometimes no mm or dd
    URL2 = r'^http://www\.(?P<rdomain>%s)\.fr/[a-z\-]+/[0-9a-z\-]+/[0-9a-z\-]+-[0-9\-]+' \
         % 'franceinfo'

    def get_id(self):
        radio_domain = self.groups[0]
        for node in self.parser.select(self.document.getroot(), 'div.node-rf_diffusion'):
            match = re.match(r'^node-(\d+)$', node.attrib.get('id', ''))
            if match:
                player_id = match.groups()[0]
                return (radio_domain, player_id)
        # if we failed, try another way (used in FIP)
        # but it might not be as accurate for others
        # (some pages have more than one of these)
        # so it's only used as a fallback
        for node in self.parser.select(self.document.getroot(), 'a.rf-player-open'):
            match = re.match(r'^/player/reecouter\?play=(\d+)$', node.attrib.get('href', ''))
            if match:
                player_id = match.groups()[0]
                return (radio_domain, player_id)
        # at least for franceinfo
        for node in self.parser.select(self.document.getroot(), '#article .emission-player a.play'):
            match = re.match(r'^song-(\d+)$', node.attrib.get('rel', ''))
            if match:
                player_id = match.groups()[0]
                return (radio_domain, player_id)


class DataPage(Page):
    def get_current(self):
        document = self.document
        title = ''
        for metas in self.parser.select(document.getroot(), 'div.metas'):
            ftitle = unicode(metas.text_content()).strip()
            if ftitle:
                title = ftitle
        # Another format (used by FIP)
        artist = document.findtext('//div[@class="metas"]//span[@class="author"]')
        if artist:
            artist = unicode(artist).strip()
            ftitle = document.findtext('//div[@class="subtitle"]')
            title = unicode(ftitle).strip() if ftitle else title
        else:
            artist = ''

        return (artist, title)


class RssPage(Page):
    def get_title(self):
        titles = []
        for heading in self.parser.select(self.document.getroot(), 'h1, h2, h3, h4'):
            # Remove newlines/multiple spaces
            words = heading.text_content()
            if words:
                for word in unicode(words).split():
                    titles.append(word)
        if len(titles):
            return ' '.join(titles)


class RadioFranceBrowser(Browser):
    DOMAIN = None
    ENCODING = 'UTF-8'
    PAGES = {r'http://.*/player/direct': DataPage,
             r'http://players.tv-radio.com/radiofrance/metadatas/([a-z]+)RSS.html': RssPage,
             PlayerPage.URL: PlayerPage,
             ReplayPage.URL: ReplayPage,
             ReplayPage.URL2: ReplayPage}

    def id2domain(self, _id):
        """
        Get the main website domain for a Radio ID.
        """
        # FIP is the only one to use "fip" but "fipradio" for the domain.
        if _id == 'fip':
            _id = 'fipradio'
        return 'www.%s.fr' % _id

    def get_current_playerjs(self, _id):
        self.location('http://%s/player/direct' % self.id2domain(_id))
        assert self.is_on_page(DataPage)

        return self.page.get_current()

    def get_current_rss(self, _id):
        self.location('http://players.tv-radio.com/radiofrance/metadatas/%sRSS.html' % _id)
        assert self.is_on_page(RssPage)

        return self.page.get_title()

    def get_current_direct(self, _id):
        json_data = self.openurl('http://%s/sites/default/files/direct.json?_=%s' % (self.id2domain(_id), int(time())))
        data = json.load(json_data)
        title = unicode(data['rf_titre_antenne']['titre'])
        artist = unicode(data['rf_titre_antenne']['interprete'])
        return (artist, title)

    def get_current_direct_large(self, _id):
        json_data = self.openurl('http://%s/sites/default/files/import_si/si_titre_antenne/FIP_player_current.json'
                                 % self.id2domain(_id))
        data = json.load(json_data)
        artist = unicode(data['current']['song']['interpreteMorceau'])
        title = unicode(data['current']['song']['titre'])
        return (artist, title)

    @id2url(RadioFranceVideo.id2url)
    def get_video(self, url):
        radio_domain = replay_id = None
        match = re.match(PlayerPage.URL, url)
        if match:
            radio_domain, replay_id = match.groups()
        elif re.match(ReplayPage.URL, url) or re.match(ReplayPage.URL2, url):
            self.location(url)
            assert self.is_on_page(ReplayPage)
            radio_domain, replay_id = self.page.get_id()
        if radio_domain and replay_id:
            radio_id = 'fip' if radio_domain == 'fipradio' else radio_domain
            _id = '%s-%s' % (radio_id, replay_id)
            return RadioFranceVideo(_id)

    @id2url(RadioFranceVideo.id2url)
    def get_url(self, url):
        self.location(url)
        assert self.is_on_page(PlayerPage)
        return self.page.get_url()
