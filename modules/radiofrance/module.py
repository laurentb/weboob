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


from weboob.capabilities.base import NotLoaded
from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audio import CapAudio, BaseAudio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module

from .browser import RadioFranceBrowser

import re
import time
from datetime import datetime

__all__ = ['RadioFranceModule']


class RadioFranceModule(Module, CapRadio, CapCollection, CapAudio):
    NAME = 'radiofrance'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '1.4'
    DESCRIPTION = u'Radios of Radio France: Inter, Info, Bleu, Culture, Musique, FIP, Le Mouv\''
    LICENSE = 'AGPLv3+'
    BROWSER = RadioFranceBrowser

    _RADIOS = {
        'franceinter': {u'title': u'France Inter',
                        u'player': u'',
                        u'live': u'programmes?xmlHttpRequest=1',
                        u'podcast': u'podcasts'},
        'franceculture': {u'title': u'France Culture',
                          u'player': u'',
                          u'live': u'programmes?xmlHttpRequest=1',
                          u'podcast': u'programmes?xmlHttpRequest=1',
                          u'selection': u''},
        'francetvinfo': {u'title': u'France Info',
                         u'player': u'en-direct/radio.html',
                         u'live': u'',
                         u'podcast': u'replay-radio',
                         u'selection': u'en-direct/radio.html'},
        'fbidf': {u'title': u'France Bleu Île-de-France (Paris)',
                  u'player': u'107-1',
                  u'live': u'grid/107-1'},
        'fipradio': {u'title': u'FIP',
                     u'player': u'player',
                     u'live': 'import_si/si_titre_antenne/FIP_player_current',
                     u'selection': u'%s' % int(time.mktime(datetime.utcnow().replace(hour=12,
                                                                                     minute=0,
                                                                                     second=0).timetuple()))},
        'francemusique': {u'title': u'France Musique',
                          u'player': u'player',
                          u'live': u'programmes?xmlHttpRequest=1',
                          u'podcast': u'emissions'},
        'mouv': {u'title': u'Le Mouv\'',
                 u'player': u'player',
                 u'live': u'lecteur_commun_json/timeline',
                 u'podcast': u'podcasts',
                 u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.utcnow().replace(hour=13,
                                                                                                              minute=0,
                                                                                                              second=0).timetuple()))},
        'fbalsace': {u'title': u'France Bleu Alsace (Strasbourg)',
                     u'player': u'alsace',
                     u'live': u'grid/alsace'},
        'fbarmorique': {u'title': u'France Bleu Armorique (Rennes)',
                        u'player': u'armorique',
                        u'live': u'grid/armorique'},
        'fbauxerre': {u'title': u'France Bleu Auxerre',
                      u'player': u'auxerre',
                      u'live': u'grid/auxerre'},
        'fbazur': {u'title': u'France Bleu Azur (Nice)',
                   u'player': u'azur',
                   u'live': u'grid/azur'},
        'fbbearn': {u'title': u'France Bleu Bearn (Pau)',
                    u'player': u'bearn',
                    u'live': u'grid/bearn'},
        'fbbelfort': {u'title': u'France Bleu Belfort',
                      u'player': u'belfort-montbeliard',
                      u'live': u'grid/belfort-montbeliard'},
        'fbberry': {u'title': u'France Bleu Berry (Châteauroux)',
                    u'player': u'berry',
                    u'live': u'grid/berry'},
        'fbbesancon': {u'title': u'France Bleu Besancon',
                       u'player': u'besancon',
                       u'live': u'grid/besancon'},
        'fbbourgogne': {u'title': u'France Bleu Bourgogne (Dijon)',
                        u'player': u'bourgogne',
                        u'live': u'grid/bourgogne'},
        'fbbreihzizel': {u'title': u'France Bleu Breizh Izel (Quimper)',
                         u'player': u'breizh-izel',
                         u'live': u'grid/breizh-izel'},
        'fbchampagne': {u'title': u'France Bleu Champagne (Reims)',
                        u'player': u'champagne-ardenne',
                        u'live': u'grid/champagne-ardenne'},
        'fbcotentin': {u'title': u'France Bleu Cotentin (Cherbourg)',
                       u'player': u'cotentin',
                       u'live': u'grid/cotentin'},
        'fbcreuse': {u'title': u'France Bleu Creuse (Gueret)',
                     u'player': u'creuse',
                     u'live': u'grid/creuse'},
        'fbdromeardeche': {u'title': u'France Bleu Drome Ardeche (Valence)',
                           u'player': u'drome-ardeche',
                           u'live': u'grid/drome-ardeche'},
        'fbelsass': {u'title': u'France Bleu Elsass',
                     u'player': 'elsass',
                     u'live': u'grid/elsass'},
        'fbgardlozere': {u'title': u'France Bleu Gard Lozère (Nîmes)',
                         u'player': u'gard-lozere',
                         u'live': u'grid/gard-lozere'},
        'fbgascogne': {u'title': u'France Bleu Gascogne (Mont-de-Marsan)',
                       u'player': u'gascogne',
                       u'live': u'grid/gascogne'},
        'fbgironde': {u'title': u'France Bleu Gironde (Bordeaux)',
                      u'player': u'gironde',
                      u'live': u'grid/gironde'},
        'fbherault': {u'title': u'France Bleu Hérault (Montpellier)',
                      u'player': u'herault',
                      u'live': u'grid/herault'},
        'fbisere': {u'title': u'France Bleu Isère (Grenoble)',
                    u'player': u'isere',
                    u'live': u'grid/isere'},
        'fblarochelle': {u'title': u'France Bleu La Rochelle',
                         u'player': u'la-rochelle',
                         u'live': u'grid/la-rochelle'},
        'fblimousin': {u'title': u'France Bleu Limousin (Limoges)',
                       u'player': u'limousin',
                       u'live': u'grid/limousin'},
        'fbloireocean': {u'title': u'France Bleu Loire Océan (Nantes)',
                         u'player': u'loire-ocean',
                         u'live': u'grid/loire-ocean'},
        'fblorrainenord': {u'title': u'France Bleu Lorraine Nord (Metz)',
                           u'player': u'lorraine-nord',
                           u'live': u'grid/lorraine-nord'},
        'fbmaine': {u'title': u'France Bleu Maine',
                    u'player': 'maine',
                    u'live': u'grid/maine'},
        'fbmayenne': {u'title': u'France Bleu Mayenne (Laval)',
                      u'player': u'mayenne',
                      u'live': u'grid/mayenne'},
        'fbnord': {u'title': u'France Bleu Nord (Lille)',
                   u'player': u'nord',
                   u'live': u'grid/nord'},
        'fbcaen': {u'title': u'France Bleu Normandie (Calvados - Orne)',
                   u'player': u'normandie-caen',
                   u'live': u'grid/normandie-caen'},
        'fbrouen': {u'title': u'France Bleu Normandie (Seine-Maritime - Eure)',
                    u'player': u'normandie-rouen',
                    u'live': u'grid/normandie-rouen'},
        'fborleans': {u'title': u'France Bleu Orléans',
                      u'player': u'orleans',
                      u'live': u'grid/orleans'},
        'fbpaysbasque': {u'title': u'France Bleu Pays Basque (Bayonne)',
                         u'player': u'pays-basque',
                         u'live': u'grid/pays-basque'},
        'fbpaysdauvergne': {u'title': u'France Bleu Pays d\'Auvergne (Clermont-Ferrand)',
                            u'player': u'pays-d-auvergne',
                            u'live': u'grid/pays-d-auvergne'},
        'fbpaysdesavoie': {u'title': u'France Bleu Pays de Savoie (Chambery)',
                           u'player': u'pays-de-savoie',
                           u'live': u'grid/pays-de-savoie'},
        'fbperigord': {u'title': u'France Bleu Périgord (Périgueux)',
                       u'player': u'perigord',
                       u'live': u'grid/perigord'},
        'fbpicardie': {u'title': u'France Bleu Picardie (Amiens)',
                       u'player': u'picardie',
                       u'live': u'grid/picardie'},
        'fbpoitou': {u'title': u'France Bleu Poitou (Poitiers)',
                     u'player': u'poitou',
                     u'live': u'grid/poitou'},
        'fbprovence': {u'title': u'France Bleu Provence (Aix-en-Provence)',
                       u'player': u'provence',
                       u'live': u'grid/provence'},
        'fbrcfm': {u'title': u'France Bleu RCFM',
                   u'player': u'rcfm',
                   u'live': u'grid/rcfm'},
        'fbsaintetienneloire': {u'title': u'France Bleu Saint-Etienne Loire',
                                u'player': u'saint-etienne-loire',
                                u'live': u'grid/saint-etienne-loire'},
        'fbroussillon': {u'title': u'France Bleu Roussillon',
                         u'player': u'roussillon',
                         u'live': u'grid/roussillon'},
        'fbsudlorraine': {u'title': u'France Bleu Sud Lorraine (Nancy)',
                          u'player': u'sud-lorraine',
                          u'live': u'grid/sud-lorraine'},
        'fbtoulouse': {u'title': u'France Bleu Toulouse',
                       u'player': u'toulouse',
                       u'live': u'grid/toulouse'},
        'fbtouraine': {u'title': u'France Bleu Touraine (Tours)',
                       u'player': u'touraine',
                       u'live': u'grid/touraine'},
        'fbvaucluse': {u'title': u'France Bleu Vaucluse (Avignon)',
                       u'player': u'vaucluse',
                       u'live': u'grid/vaucluse'},
    }

    def iter_resources(self, objs, split_path):
        if len(split_path) == 0:
            for _id, item in sorted(self._RADIOS.items()):
                if not _id.startswith('fb'):
                    yield Collection([_id], item['title'])
            yield Collection([u'francebleu'], u'France Bleu')

        elif split_path[0] == u'francebleu':
            if len(split_path) == 1:
                for _id, item in sorted(self._RADIOS.items()):
                    if _id.startswith('fb'):
                        yield Collection([_id], item['title'])

            elif len(split_path) > 1 and split_path[1] in self._RADIOS:
                if len(split_path) == 2:
                    yield Collection([split_path[0], u'direct'], u'Direct')
                if 'selection' in self._RADIOS[split_path[1]]:
                    yield Collection([split_path[0], u'selection'], u'Selection')

                elif len(split_path) == 3 and split_path[2] == 'selection':
                    selection_url = self._RADIOS[split_path[1]]['selection']
                    for item in self.browser.get_selection('francebleu', selection_url, split_path[1]):
                        yield item

                elif len(split_path) == 3 and split_path[2] == 'direct':
                    yield self.get_radio(split_path[1])

            else:
                raise CollectionNotFound(split_path)

        elif len(split_path) == 1:
            yield Collection([split_path[0], u'direct'], u'Direct')
            if 'selection' in self._RADIOS[split_path[0]]:
                yield Collection([split_path[0], u'selection'], u'Selection')
            if 'podcast' in self._RADIOS[split_path[0]]:
                yield Collection([split_path[0], u'podcasts'], u'Podcast')

        elif len(split_path) == 2 and split_path[1] == 'selection':
            for _id, item in sorted(self._RADIOS.iteritems()):
                if _id == split_path[0]:
                    if 'selection' in self._RADIOS[_id]:
                        selection_url = self._RADIOS[_id]['selection']
                        for item in self.browser.get_selection(_id, selection_url, _id):
                            yield item
                        break

        elif len(split_path) == 2 and split_path[1] == 'podcasts':
            for item in self.browser.get_podcast_emissions(split_path[0],
                                                           self._RADIOS[split_path[0]]['podcast'],
                                                           split_path):
                yield item

        elif len(split_path) == 2 and split_path[1] == 'direct':
            yield self.get_radio(split_path[0])

        elif len(split_path) == 3:
            podcasts_url = split_path[-1]
            if split_path[0] == 'franceculture':
                podcasts_url = self.browser.get_france_culture_podcasts_url(split_path[-1])
            elif split_path[0] == 'francetvinfo':
                podcasts_url = self.browser.get_francetvinfo_podcasts_url(split_path[-1])
            if podcasts_url:
                for item in self.browser.get_podcasts(podcasts_url):
                    yield item

        else:
            raise CollectionNotFound(split_path)

    def get_radio(self, radio):

        def create_stream(url, hd=True):
            stream = BaseAudioStream(0)
            if hd:
                stream.bitrate = 128
            else:
                stream.bitrate = 32
                url = url.replace('midfi', 'lofi')

            stream.format = u'mp3'
            stream.title = u'%s kbits/s' % (stream.bitrate)
            stream.url = url
            return stream

        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if radio.id not in self._RADIOS:
            return None

        title = self._RADIOS[radio.id]['title']
        player_url = self._RADIOS[radio.id]['player']
        radio.title = title
        radio.description = title
        radio_name = radio.id if not radio.id.startswith('fb') else 'francebleu'
        url = self.browser.get_radio_url(radio_name, player_url)

        self.fillobj(radio, ('current', ))
        radio.streams = [create_stream(url), create_stream(url, False)]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            title = self._RADIOS[radio.id]['title']
            live_url = self._RADIOS[radio.id]['live']
            radio_name = radio.id if not radio.id.startswith('fb') else 'francebleu'
            artist, title = self.browser.get_current(radio_name, live_url)
            if not radio.current or radio.current is NotLoaded:
                radio.current = StreamInfo(0)
            radio.current.what = title
            radio.current.who = artist
        return radio

    def fill_audio(self, audio, fields):
        if 'thumbnail' in fields and audio.thumbnail:
            audio.thumbnail.data = self.browser.open(audio.thumbnail.url)
        return audio

    def get_radio_id(self, audio_id):
        m = re.match('^\w+\.(\w+)\..*', audio_id)
        if m:
            return m.group(1)
        return ''

    def search_audio(self, pattern, sortby=CapAudio.SEARCH_RELEVANCE):
        for radio in self._RADIOS:
            if 'selection' in self._RADIOS[radio]:
                selection_url = self._RADIOS[radio]['selection']
                radio_url = radio if not radio.startswith('fb') else 'francebleu'
                for item in self.browser.get_selection(radio_url, selection_url, radio):
                    if pattern.upper() in item.title.upper():
                        yield item

            if 'podcast' in self._RADIOS[radio]:
                podcast_url = self._RADIOS[radio]['podcast']
                radio_url = radio if not radio.startswith('fb') else 'francebleu'
                for item in self.browser.get_podcast_emissions(radio_url,
                                                               podcast_url,
                                                               [radio]):
                    if pattern.upper() in item.title.upper():
                        podcasts_url = item.id
                        if radio == 'franceculture':
                            podcasts_url = self.browser.get_france_culture_podcasts_url(item.id)
                        elif radio == 'francetvinfo':
                            podcasts_url = self.browser.get_francetvinfo_podcasts_url(item.id)

                        for pod in self.browser.get_podcasts(podcasts_url):
                            yield pod

    def get_audio(self, _id):
        radio = self.get_radio_id(_id)
        if radio in self._RADIOS:
            if 'selection' in self._RADIOS[radio]:
                selection_url = self._RADIOS[radio]['selection']
                radio_url = radio if not radio.startswith('fb') else 'francebleu'
                return self.browser.get_audio(_id, radio_url, selection_url, radio)
        elif radio == 'podcast':
            m = re.match('audio\.podcast\.(\d*)-.*', _id)
            if m:
                for item in self.browser.get_podcasts(m.group(1)):
                    if _id == item.id:
                        return item

    def iter_radios_search(self, pattern):
        for key, radio in self._RADIOS.iteritems():
            if pattern.lower() in radio['title'].lower() or pattern.lower() in key.lower():
                yield self.get_radio(key)

    OBJECTS = {Radio: fill_radio, BaseAudio: fill_audio}
