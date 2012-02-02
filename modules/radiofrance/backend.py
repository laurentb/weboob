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


from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.collection import ICapCollection, CollectionNotFound
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser, BasePage

from StringIO import StringIO
from time import time

try:
    import json
except ImportError:
    import simplejson as json


__all__ = ['RadioFranceBackend']


class DataPage(BasePage):
    def get_title(self):
        for metas in self.parser.select(self.document.getroot(), 'div.metas'):
            title = unicode(metas.text_content()).strip()
            if len(title):
                return title


class RadioFranceBrowser(BaseBrowser):
    DOMAIN = None
    ENCODING = 'UTF-8'
    PAGES = {r'/playerjs/direct/donneesassociees/html\?guid=$': DataPage}

    def get_current_playerjs(self, id):
        self.location('http://www.%s.fr/playerjs/direct/donneesassociees/html?guid=' % id)
        assert self.is_on_page(DataPage)

        return self.page.get_title()

    def get_current_direct(self, id):
        json_data = self.openurl('http://www.%s.fr/sites/default/files/direct.json?_=%s' % (id, int(time())))
        data = json.load(json_data)

        document = self.parser.parse(StringIO(data.get('html')))
        artist = document.findtext('//span[@class="artiste"]')
        title = document.findtext('//span[@class="titre"]')
        artist = unicode(artist) if artist else None
        title = unicode(title) if title else None
        return (artist, title)


class RadioFranceBackend(BaseBackend, ICapRadio, ICapCollection):
    NAME = 'radiofrance'
    MAINTAINER = 'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '0.a'
    DESCRIPTION = u'The radios of Radio France (Inter, Culture, Le Mouv\', etc.)'
    LICENSE = 'AGPLv3+'
    BROWSER = RadioFranceBrowser

    _MP3_URL =  u'http://mp3.live.tv-radio.com/%s/all/%s.mp3'
    _MP3_HD_URL =  u'http://mp3.live.tv-radio.com/%s/all/%shautdebit.mp3'
    _RADIOS = {'franceinter': (u'France Inter', True),
        'franceculture': (u'France Culture', True),
        'franceinfo': (u'France Info', False),
        'fbidf': (u'France Bleu Île-de-France (Paris)', True),
        'fip': (u'FIP', True),
        'francemusique': (u'France Musique', True),
        'lemouv': (u'Le Mouv\'', True),
        'fbalsace': (u'France Bleu Alsace (Strasbourg)', False),
        'fbarmorique': (u'France Bleu Armorique (Rennes)', False),
        'fbauxerre': (u'France Bleu Auxerre', False),
        'fbazur': (u'France Bleu Azur (Nice)', False),
        'fbbassenormandie': (u'France Bleu Basse Normandie (Caen)', False),
        'fbbearn': (u'France Bleu Bearn (Pau)', False),
        'fbbelfort': (u'France Bleu Belfort', False),
        'fbberry': (u'France Bleu Berry (Châteauroux)', False),
        'fbbesancon': (u'France Bleu Besancon', False),
        'fbbourgogne': (u'France Bleu Bourgogne (Dijon)', False),
        'fbbreizizel': (u'France Bleu Breiz Izel (Quimper)', False),
        'fbchampagne': (u'France Bleu Champagne (Reims)', False),
        'fbcotentin': (u'France Bleu Cotentin (Cherbourg)', False),
        'fbcreuse': (u'France Bleu Creuse (Gueret)', False),
        'fbdromeardeche': (u'France Bleu Drome Ardeche (Valence)', False),
        'fbfrequenzamora': (u'France Bleu Frequenza Mora (Bastia - Corse)', False),
        'fbgardlozere': (u'France Bleu Gard Lozère (Nîmes)', False),
        'fbgascogne': (u'France Bleu Gascogne (Mont-de-Marsan)', False),
        'fbgironde': (u'France Bleu Gironde (Bordeaux)', False),
        'fbhautenormandie': (u'France Bleu Haute Normandie (Rouen)', False),
        'fbherault': (u'France Bleu Hérault (Montpellier)', False),
        'fbisere': (u'France Bleu Isère (Grenoble)', False),
        'fblarochelle': (u'France Bleu La Rochelle', False),
        'fblimousin': (u'France Bleu Limousin (Limoges)', False),
        'fbloireocean': (u'France Bleu Loire Océan (Nantes)', False),
        'fblorrainenord': (u'France Bleu Lorraine Nord (Metz)', False),
        'fbmayenne': (u'France Bleu Mayenne (Laval)', False),
        'fbnord': (u'France Bleu Nord (Lille)', False),
        'fborleans': (u'France Bleu Orléans', False),
        'fbpaysbasque': (u'France Bleu Pays Basque (Bayonne)', False),
        'fbpaysdauvergne': (u'France Bleu Pays d\'Auvergne (Clermont-Ferrand)', False),
        'fbpaysdesavoie': (u'France Bleu Pays de Savoie (Chambery)', False),
        'fbperigord': (u'France Bleu Périgord (Périgueux)', False),
        'fbpicardie': (u'France Bleu Picardie (Amiens)', False),
        'fbpoitou': (u'France Bleu Poitou (Poitiers)', False),
        'fbprovence': (u'France Bleu Provence (Aix-en-Provence)', False),
        'fbroussillon': (u'France Bleu Roussillon (Perpigan)', False),
        'fbsudlorraine': (u'France Bleu Sud Lorraine (Nancy)', False),
        'fbtoulouse': (u'France Bleu Toulouse', False),
        'fbtouraine': (u'France Bleu Touraine (Tours)', False),
        'fbvaucluse': (u'France Bleu Vaucluse (Avignon)', False),
    }

    _PLAYERJS_RADIOS = ('franceinter',
                        'franceculture',
                        'franceinfo',
                        'lemouv',
                        )

    _DIRECTJSON_RADIOS = ('lemouv', 'franceinter', )

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

        title, hd = self._RADIOS[radio.id]
        radio.title = title
        radio.description = title

        if hd:
            url = self._MP3_HD_URL % (radio.id, radio.id)
        else:
            url = self._MP3_URL % (radio.id, radio.id)

        self.fillobj(radio, ('current', ))

        stream = Stream(0)
        stream.title = u'128kbits/s'
        stream.url = url
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            if not radio.current:
                radio.current = Emission(0)
            radio.current.artist = None
            radio.current.title = None
            if radio.id in self._PLAYERJS_RADIOS:
                radio.current.title = self.browser.get_current_playerjs(radio.id)
            if radio.id in self._DIRECTJSON_RADIOS:
                artist, title = self.browser.get_current_direct(radio.id)
                if artist:
                    radio.current.artist = artist
                if title:
                    if radio.current.title:
                        radio.current.title = "%s [%s]" % (title, radio.current.title)
                    else:
                        radio.current.title = title
        return radio

    OBJECTS = {Radio: fill_radio}
