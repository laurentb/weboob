# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.collection import ICapCollection, CollectionNotFound
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser, BasePage, BrowserUnavailable


__all__ = ['NovaBackend']


class HistoryPage(BasePage):
    def on_loaded(self):
        h2 = self.parser.select(self.document.getroot(), 'h2')
        if len(h2) > 0 and h2[0].text == 'Site off-line':
            raise BrowserUnavailable('Website is currently offline')

    def get_current(self):
        for div in self.parser.select(self.document.getroot(), 'div#rubrique_contenu div.resultat'):
            artist = self.parser.select(div, 'span#artiste', 1).find('a').text
            title = self.parser.select(div, 'span#titre', 1).text
            return unicode(artist).strip(), unicode(title).strip()

class NovaBrowser(BaseBrowser):
    DOMAIN = u'www.novaplanet.com'
    PAGES = {r'http://www.novaplanet.com/cetaitquoicetitre/radionova/\d*': HistoryPage,
            }

    def get_current(self):
        self.location('/cetaitquoicetitre/radionova/')
        assert self.is_on_page(HistoryPage)

        return self.page.get_current()

class NovaBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'nova'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.9.1'
    DESCRIPTION = u'Nova french radio'
    LICENSE = 'AGPLv3+'
    BROWSER = NovaBrowser

    _RADIOS = {'nova':     (u'Radio Nova',  u'Radio nova',   u'http://broadcast.infomaniak.net:80/radionova-high.mp3'),
              }

    def iter_resources(self, splited_path):
        if len(splited_path) > 0:
            raise CollectionNotFound()

        for id in self._RADIOS.iterkeys():
            yield self.get_radio(id)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources([]):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if not radio.id in self._RADIOS:
            return None

        title, description, url = self._RADIOS[radio.id]
        radio.title = title
        radio.description = description

        artist, title = self.browser.get_current()
        current = Emission(0)
        current.artist = artist
        current.title = title
        radio.current = current

        stream = Stream(0)
        stream.title = u'128kbits/s'
        stream.url = url
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = Emission(0)
            radio.current.artist, radio.current.title = self.browser.get_current()
        return radio

    OBJECTS = {Radio: fill_radio}
