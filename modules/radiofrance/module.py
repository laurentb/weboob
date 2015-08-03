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
    VERSION = '1.1'
    DESCRIPTION = u'Radios of Radio France: Inter, Info, Bleu, Culture, Musique, FIP, Le Mouv\''
    LICENSE = 'AGPLv3+'
    BROWSER = RadioFranceBrowser

    _RADIOS = {
        'franceinter': {u'title': u'France Inter',
                        u'player': u'player',
                        u'live': u'lecteur_commun_json/timeline',
                        u'podcast': u'podcasts',
                        u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'franceculture': {u'title': u'France Culture',
                          u'player': u'player',
                          u'live': u'lecteur_commun_json/timeline',
                          u'podcast': u'podcasts',
                          u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'franceinfo': {u'title': u'France Info',
                       u'player': u'player',
                       u'live': u'lecteur_commun_json/timeline',
                       u'podcast': u'programmes-chroniques/podcasts',
                       u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbidf': {u'title': u'France Bleu Île-de-France (Paris)',
                  u'player': u'player/france-bleu-107-1',
                  u'live': u'lecteur_commun_json/timeline-9753',
                  u'selection': u'lecteur_commun_json/reecoute-9753-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fipradio': {u'title': u'FIP',
                     u'player': u'player',
                     u'live': 'import_si/si_titre_antenne/FIP_player_current',
                     u'selection': u'%s' % int(time.mktime(datetime.now().replace(hour=12, minute=0, second=0).timetuple()))},
        'francemusique': {u'title': u'France Musique',
                          u'player': u'player',
                          u'live': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple())),
                          u'podcast': u'emissions',
                          u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'mouv': {u'title': u'Le Mouv\'',
                 u'player': u'player',
                 u'live': u'lecteur_commun_json/timeline',
                 u'podcast': u'podcasts',
                 u'selection': u'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbalsace': {u'title': u'France Bleu Alsace (Strasbourg)',
                     u'player': u'player/station/france-bleu-alsace',
                     u'live': u'lecteur_commun_json/timeline-13085',
                     u'selection': u'lecteur_commun_json/reecoute-13085-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbarmorique': {u'title': u'France Bleu Armorique (Rennes)',
                        u'player': u'player/station/france-bleu-armorique',
                        u'live': u'lecteur_commun_json/timeline-13087',
                        u'selection': u'lecteur_commun_json/reecoute-13087-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbauxerre': {u'title': u'France Bleu Auxerre',
                      u'player': u'player/station/france-bleu-auxerre',
                      u'live': u'lecteur_commun_json/timeline-11219',
                      u'selection': u'lecteur_commun_json/reecoute-11219-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbazur': {u'title': u'France Bleu Azur (Nice)',
                   u'player': u'player/station/france-bleu-azur',
                   u'live': u'lecteur_commun_json/timeline-13089',
                   u'selection': u'lecteur_commun_json/reecoute-13089-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbassenormandie': {u'title': u'France Bleu Basse Normandie (Caen)',
                             u'player': u'player/station/france-bleu-bassenormandie',
                             u'live': u'lecteur_commun_json/timeline-13091',
                             u'selection': u'lecteur_commun_json/reecoute-13091-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbearn': {u'title': u'France Bleu Bearn (Pau)',
                    u'player': u'player/station/france-bleu-bearn',
                    u'live': u'lecteur_commun_json/timeline-13093',
                    u'selection': u'lecteur_commun_json/reecoute-13093-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbelfort': {u'title': u'France Bleu Belfort',
                      u'player': u'player/station/france-bleu-belfort',
                      u'live': u'lecteur_commun_json/timeline-13095',
                      u'selection': u'lecteur_commun_json/reecoute-13095-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbberry': {u'title': u'France Bleu Berry (Châteauroux)',
                    u'player': u'player/station/france-bleu-berry',
                    u'live': u'lecteur_commun_json/timeline-11223',
                    u'selection': u'lecteur_commun_json/reecoute-11223-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbesancon': {u'title': u'France Bleu Besancon',
                       u'player': u'player/station/france-bleu-besancon',
                       u'live': u'lecteur_commun_json/timeline-13097',
                       u'selection': u'lecteur_commun_json/reecoute-13097-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbourgogne': {u'title': u'France Bleu Bourgogne (Dijon)',
                        u'player': u'player/station/france-bleu-bourgogne',
                        u'live': u'lecteur_commun_json/timeline-13099',
                        u'selection': u'lecteur_commun_json/reecoute-13099-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbbreizizel': {u'title': u'France Bleu Breiz Izel (Quimper)',
                        u'player': u'player/station/france-bleu-breizizel',
                        u'live': u'lecteur_commun_json/timeline-13101',
                        u'selection': u'lecteur_commun_json/reecoute-13101-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbchampagne': {u'title': u'France Bleu Champagne (Reims)',
                        u'player': u'player/station/france-bleu-champagne',
                        u'live': u'lecteur_commun_json/timeline-13103',
                        u'selection': u'lecteur_commun_json/reecoute-13103-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbcotentin': {u'title': u'France Bleu Cotentin (Cherbourg)',
                       u'player': u'player/station/france-bleu-cotentin',
                       u'live': u'lecteur_commun_json/timeline-13105',
                       u'selection': u'lecteur_commun_json/reecoute-13105-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbcreuse': {u'title': u'France Bleu Creuse (Gueret)',
                     u'player': u'player/station/france-bleu-creuse',
                     u'live': u'lecteur_commun_json/timeline-13107',
                     u'selection': u'lecteur_commun_json/reecoute-13107-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbdromeardeche': {u'title': u'France Bleu Drome Ardeche (Valence)',
                           u'player': u'player/station/france-bleu-dromeardeche',
                           u'live': u'lecteur_commun_json/timeline-13109',
                           u'selection': u'lecteur_commun_json/reecoute-13109-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbelsass': {u'title': u'France Bleu Elsass',
                     u'player': 'player/station/france-bleu-elsass',
                     u'live': u'lecteur_commun_json/timeline-19370',
                     u'selection': u'lecteur_commun_json/reecoute-19370-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbgardlozere': {u'title': u'France Bleu Gard Lozère (Nîmes)',
                         u'player': u'player/station/france-bleu-gardlozere',
                         u'live': u'lecteur_commun_json/timeline-13111',
                         u'selection': u'lecteur_commun_json/reecoute-13111-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbgascogne': {u'title': u'France Bleu Gascogne (Mont-de-Marsan)',
                       u'player': u'player/station/france-bleu-gascogne',
                       u'live': u'lecteur_commun_json/timeline-13113',
                       u'selection': u'lecteur_commun_json/reecoute-13113-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbgironde': {u'title': u'France Bleu Gironde (Bordeaux)',
                      u'player': u'player/station/france-bleu-gironde',
                      u'live': u'lecteur_commun_json/timeline-13115',
                      u'selection': u'lecteur_commun_json/reecoute-13115-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbhautenormandie': {u'title': u'France Bleu Haute Normandie (Rouen)',
                             u'player': u'player/station/france-bleu-hautenormandie',
                             u'live': u'lecteur_commun_json/timeline-13117',
                             u'selection': u'lecteur_commun_json/reecoute-13117-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbherault': {u'title': u'France Bleu Hérault (Montpellier)',
                      u'player': u'player/station/france-bleu-herault',
                      u'live': u'lecteur_commun_json/timeline-11231',
                      u'selection': u'lecteur_commun_json/reecoute-11231-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbisere': {u'title': u'France Bleu Isère (Grenoble)',
                    u'player': u'player/station/france-bleu-isere',
                    u'live': u'lecteur_commun_json/timeline-13119',
                    u'selection': u'lecteur_commun_json/reecoute-13119-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fblarochelle': {u'title': u'France Bleu La Rochelle',
                         u'player': u'player/station/france-bleu-larochelle',
                         u'live': u'lecteur_commun_json/timeline-13121',
                         u'selection': u'lecteur_commun_json/reecoute-13121-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fblimousin': {u'title': u'France Bleu Limousin (Limoges)',
                       u'player': u'player/station/france-bleu-limousin',
                       u'live': u'lecteur_commun_json/timeline-13123',
                       u'selection': u'lecteur_commun_json/reecoute-13123-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbloireocean': {u'title': u'France Bleu Loire Océan (Nantes)',
                         u'player': u'player/station/france-bleu-loireocean',
                         u'live': u'lecteur_commun_json/timeline-13125',
                         u'selection': u'lecteur_commun_json/reecoute-13125-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fblorrainenord': {u'title': u'France Bleu Lorraine Nord (Metz)',
                           u'player': u'player/station/france-bleu-lorrainenord',
                           u'live': u'lecteur_commun_json/timeline-13127',
                           u'selection': u'lecteur_commun_json/reecoute-13127-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbmaine': {u'title': u'France Bleu Maine',
                    u'player': 'player/station/france-bleu-maine',
                    u'live': u'lecteur_commun_json/timeline-13129',
                    u'selection': u'lecteur_commun_json/reecoute-13129-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbmayenne': {u'title': u'France Bleu Mayenne (Laval)',
                      u'player': u'player/station/france-bleu-mayenne',
                      u'live': u'lecteur_commun_json/timeline-13131',
                      u'selection': u'lecteur_commun_json/reecoute-13131-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbnord': {u'title': u'France Bleu Nord (Lille)',
                   u'player': u'player/station/france-bleu-nord',
                   u'live': u'lecteur_commun_json/timeline-11235',
                   u'selection': u'lecteur_commun_json/reecoute-11235-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fborleans': {u'title': u'France Bleu Orléans',
                      u'player': u'player/station/france-bleu-orleans',
                      u'live': u'lecteur_commun_json/timeline-13133',
                      u'selection': u'lecteur_commun_json/reecoute-13133-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbpaysbasque': {u'title': u'France Bleu Pays Basque (Bayonne)',
                         u'player': u'player/station/france-bleu-paysbasque',
                         u'live': u'lecteur_commun_json/timeline-13135',
                         u'selection': u'lecteur_commun_json/reecoute-13135-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbpaysdauvergne': {u'title': u'France Bleu Pays d\'Auvergne (Clermont-Ferrand)',
                            u'player': u'player/station/france-bleu-paysdauvergne',
                            u'live': u'lecteur_commun_json/timeline-11237',
                            u'selection': u'lecteur_commun_json/reecoute-11237-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbpaysdesavoie': {u'title': u'France Bleu Pays de Savoie (Chambery)',
                           u'player': u'player/station/france-bleu-paysdesavoie',
                           u'live': u'lecteur_commun_json/timeline-11239',
                           u'selection': u'lecteur_commun_json/reecoute-11239-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbperigord': {u'title': u'France Bleu Périgord (Périgueux)',
                       u'player': u'player/station/france-bleu-perigord',
                       u'live': u'lecteur_commun_json/timeline-13137',
                       u'selection': u'lecteur_commun_json/reecoute-13137-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbpicardie': {u'title': u'France Bleu Picardie (Amiens)',
                       u'player': u'player/station/france-bleu-picardie',
                       u'live': u'lecteur_commun_json/timeline-13139',
                       u'selection': u'lecteur_commun_json/reecoute-13139-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbpoitou': {u'title': u'France Bleu Poitou (Poitiers)',
                     u'player': u'player/station/france-bleu-poitou',
                     u'live': u'lecteur_commun_json/timeline-13141',
                     u'selection': u'lecteur_commun_json/reecoute-13141-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbprovence': {u'title': u'France Bleu Provence (Aix-en-Provence)',
                       u'player': u'player/station/france-bleu-provence',
                       u'live': u'lecteur_commun_json/timeline-11241',
                       u'selection': u'lecteur_commun_json/reecoute-11241-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbrcfm': {u'title': u'France Bleu RCFM',
                   u'player': u'player/station/france-bleu-rcfm',
                   u'live': u'lecteur_commun_json/timeline-13143',
                   u'selection': u'lecteur_commun_json/reecoute-13143-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbsaintetienneloire': {u'title': u'France Bleu Saint-Etienne Loire',
                                u'player': u'player/station/france-bleu-saint-etienne-loire',
                                u'live': u'lecteur_commun_json/timeline-60434',
                                u'selection': u'lecteur_commun_json/reecoute-60434-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbroussillon': {u'title': u'France Bleu Roussillon',
                         u'player': u'player/station/france-bleu-roussillon',
                         u'live': u'lecteur_commun_json/timeline-11243',
                         u'selection': u'lecteur_commun_json/reecoute-11243-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbsudlorraine': {u'title': u'France Bleu Sud Lorraine (Nancy)',
                          u'player': u'player/station/france-bleu-sudlorraine',
                          u'live': u'lecteur_commun_json/timeline-13145',
                          u'selection': u'lecteur_commun_json/reecoute-13145-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbtoulouse': {u'title': u'France Bleu Toulouse',
                       u'player': u'player/station/france-bleu-toulouse',
                       u'live': u'lecteur_commun_json/timeline-13147',
                       u'selection': u'lecteur_commun_json/reecoute-13147-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbtouraine': {u'title': u'France Bleu Touraine (Tours)',
                       u'player': u'player/station/france-bleu-touraine',
                       u'live': u'lecteur_commun_json/timeline-13149',
                       u'selection': u'lecteur_commun_json/reecoute-13149-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
        'fbvaucluse': {u'title': u'France Bleu Vaucluse (Avignon)',
                       u'player': u'player/station/france-bleu-vaucluse',
                       u'live': u'lecteur_commun_json/timeline-13151',
                       u'selection': u'lecteur_commun_json/reecoute-13151-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))},
    }

    def iter_resources(self, objs, split_path):
        if len(split_path) == 0:
            for _id, item in sorted(self._RADIOS.iteritems()):
                if not _id.startswith('fb'):
                    yield Collection([_id], item['title'])
            yield Collection([u'francebleu'], u'France Bleu')

        elif split_path[0] == u'francebleu':
            if len(split_path) == 1:
                for _id, item in sorted(self._RADIOS.iteritems()):
                    if _id.startswith('fb'):
                        yield Collection([_id], item['title'])

            elif len(split_path) > 1 and split_path[1] in self._RADIOS:
                if len(split_path) == 2:
                    yield Collection([split_path[0], u'direct'], u'Direct')
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
            yield Collection([split_path[0], u'selection'], u'Selection')
            if 'podcast' in self._RADIOS[split_path[0]]:
                yield Collection([split_path[0], u'podcasts'], u'Podcast')

        elif len(split_path) == 2 and split_path[1] == 'selection':
            for _id, item in sorted(self._RADIOS.iteritems()):
                if _id == split_path[0]:
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
                url = url.replace('midfi128', 'lofi32')

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
            json_url = self._RADIOS[radio.id]['live']
            radio_name = radio.id if not radio.id.startswith('fb') else 'francebleu'
            artist, title = self.browser.get_current(radio_name, json_url)
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
            selection_url = self._RADIOS[radio]['selection']
            radio_url = radio if not radio.startswith('fb') else 'francebleu'
            for item in self.browser.search_audio(pattern, radio_url, selection_url, radio):
                yield item

    def get_audio(self, _id):
        radio = self.get_radio_id(_id)
        if radio in self._RADIOS:
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
