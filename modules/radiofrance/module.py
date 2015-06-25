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
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module

from .browser import RadioFranceBrowser

import time
from datetime import datetime

__all__ = ['RadioFranceModule']


class RadioFranceModule(Module, CapRadio, CapCollection):
    NAME = 'radiofrance'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '1.1'
    DESCRIPTION = u'Radios of Radio France: Inter, Info, Bleu, Culture, Musique, FIP, Le Mouv\''
    LICENSE = 'AGPLv3+'
    BROWSER = RadioFranceBrowser

    _RADIOS = {'franceinter': (u'France Inter', 'player', 'lecteur_commun_json/timeline'),
        'franceculture': (u'France Culture', 'player', 'lecteur_commun_json/timeline'),
        'franceinfo': (u'France Info', 'player', 'lecteur_commun_json/timeline'),
        'fbidf': (u'France Bleu Île-de-France (Paris)', 'station/france-bleu-107-1', 'lecteur_commun_json/timeline-9753'),
        'fipradio': (u'FIP', 'player', 'import_si/si_titre_antenne/FIP_player_current'),
        'francemusique': (u'France Musique', 'player', 'lecteur_commun_json/reecoute-%s' % int(time.mktime(datetime.now().replace(hour=14, minute=0, second=0).timetuple()))),
        'mouv': (u'Le Mouv\'', 'player', 'lecteur_commun_json/timeline'),
        'fbalsace': (u'France Bleu Alsace (Strasbourg)', 'player/station/france-bleu-alsace', 'lecteur_commun_json/timeline-13085'),
        'fbarmorique': (u'France Bleu Armorique (Rennes)', 'player/station/france-bleu-armorique', 'lecteur_commun_json/timeline-13087'),
        'fbauxerre': (u'France Bleu Auxerre', 'player/station/france-bleu-auxerre', 'lecteur_commun_json/timeline-11219'),
        'fbazur': (u'France Bleu Azur (Nice)', 'player/station/france-bleu-azur', 'lecteur_commun_json/timeline-13089'),
        'fbbassenormandie': (u'France Bleu Basse Normandie (Caen)', 'player/station/france-bleu-bassenormandie', 'lecteur_commun_json/timeline-13091'),
        'fbbearn': (u'France Bleu Bearn (Pau)', 'player/station/france-bleu-bearn', 'lecteur_commun_json/timeline-13093'),
        'fbbelfort': (u'France Bleu Belfort', 'player/station/france-bleu-belfort', 'lecteur_commun_json/timeline-13095'),
        'fbberry': (u'France Bleu Berry (Châteauroux)', 'player/station/france-bleu-berry', 'lecteur_commun_json/timeline-11223'),
        'fbbesancon': (u'France Bleu Besancon', 'player/station/france-bleu-besancon', 'lecteur_commun_json/timeline-13097'),
        'fbbourgogne': (u'France Bleu Bourgogne (Dijon)', 'player/station/france-bleu-bourgogne', 'lecteur_commun_json/timeline-13099'),
        'fbbreizizel': (u'France Bleu Breiz Izel (Quimper)', 'player/station/france-bleu-breizizel', 'lecteur_commun_json/timeline-13101'),
        'fbchampagne': (u'France Bleu Champagne (Reims)', 'player/station/france-bleu-champagne', 'lecteur_commun_json/timeline-13103'),
        'fbcotentin': (u'France Bleu Cotentin (Cherbourg)', 'player/station/france-bleu-cotentin', 'lecteur_commun_json/timeline-13105'),
        'fbcreuse': (u'France Bleu Creuse (Gueret)', 'player/station/france-bleu-creuse', 'lecteur_commun_json/timeline-13107'),
        'fbdromeardeche': (u'France Bleu Drome Ardeche (Valence)', 'player/station/france-bleu-dromeardeche', 'lecteur_commun_json/timeline-13109'),
        'fbelsass': (u'France Bleu Elsass', '/player/station/france-bleu-elsass', 'lecteur_commun_json/timeline-19370'),
        'fbgardlozere': (u'France Bleu Gard Lozère (Nîmes)', 'player/station/france-bleu-gardlozere', 'lecteur_commun_json/timeline-13111'),
        'fbgascogne': (u'France Bleu Gascogne (Mont-de-Marsan)', 'player/station/france-bleu-gascogne', 'lecteur_commun_json/timeline-13113'),
        'fbgironde': (u'France Bleu Gironde (Bordeaux)', 'player/station/france-bleu-gironde', 'lecteur_commun_json/timeline-13115'),
        'fbhautenormandie': (u'France Bleu Haute Normandie (Rouen)', 'player/station/france-bleu-hautenormandie', 'lecteur_commun_json/timeline-13117'),
        'fbherault': (u'France Bleu Hérault (Montpellier)', 'player/station/france-bleu-herault', 'lecteur_commun_json/timeline-11231'),
        'fbisere': (u'France Bleu Isère (Grenoble)', 'player/station/france-bleu-isere', 'lecteur_commun_json/timeline-13119'),
        'fblarochelle': (u'France Bleu La Rochelle', 'player/station/france-bleu-larochelle', 'lecteur_commun_json/timeline-13121'),
        'fblimousin': (u'France Bleu Limousin (Limoges)', 'player/station/france-bleu-limousin', 'lecteur_commun_json/timeline-13123'),
        'fbloireocean': (u'France Bleu Loire Océan (Nantes)', 'player/station/france-bleu-loireocean', 'lecteur_commun_json/timeline-13125'),
        'fblorrainenord': (u'France Bleu Lorraine Nord (Metz)', 'player/station/france-bleu-lorrainenord', 'lecteur_commun_json/timeline-13127'),
        'fbmaine': (u'France Bleu Maine', '/player/station/france-bleu-maine', 'lecteur_commun_json/timeline-13129'),
        'fbmayenne': (u'France Bleu Mayenne (Laval)', 'player/station/france-bleu-mayenne', 'lecteur_commun_json/timeline-13131'),
        'fbnord': (u'France Bleu Nord (Lille)', 'player/station/france-bleu-nord', 'lecteur_commun_json/timeline-11235'),
        'fborleans': (u'France Bleu Orléans', 'player/station/france-bleu-orleans', 'lecteur_commun_json/timeline-13133'),
        'fbpaysbasque': (u'France Bleu Pays Basque (Bayonne)', 'player/station/france-bleu-paysbasque', 'lecteur_commun_json/timeline-13135'),
        'fbpaysdauvergne': (u'France Bleu Pays d\'Auvergne (Clermont-Ferrand)', 'player/station/france-bleu-paysdauvergne', 'lecteur_commun_json/timeline-11237'),
        'fbpaysdesavoie': (u'France Bleu Pays de Savoie (Chambery)', 'player/station/france-bleu-paysdesavoie', 'lecteur_commun_json/timeline-11239'),
        'fbperigord': (u'France Bleu Périgord (Périgueux)', 'player/station/france-bleu-perigord', 'lecteur_commun_json/timeline-13137'),
        'fbpicardie': (u'France Bleu Picardie (Amiens)', 'player/station/france-bleu-picardie', 'lecteur_commun_json/timeline-13139'),
        'fbpoitou': (u'France Bleu Poitou (Poitiers)', 'player/station/france-bleu-poitou', 'lecteur_commun_json/timeline-13141'),
        'fbprovence': (u'France Bleu Provence (Aix-en-Provence)', 'player/station/france-bleu-provence', 'lecteur_commun_json/timeline-11241'),
        'fbrcfm': (u'France Bleu RCFM', 'player/station/france-bleu-rcfm', 'lecteur_commun_json/timeline-13143'),
        'fbsaintetienneloire': (u'France Bleu Saint-Etienne Loire', 'player/station/france-bleu-saint-etienne-loire', 'lecteur_commun_json/timeline-60434'),
        'fbroussillon': (u'France Bleu Roussillon', 'player/station/france-bleu-roussillon', 'lecteur_commun_json/timeline-11243'),
        'fbsudlorraine': (u'France Bleu Sud Lorraine (Nancy)', 'player/station/france-bleu-sudlorraine', 'lecteur_commun_json/timeline-13145'),
        'fbtoulouse': (u'France Bleu Toulouse', 'player/station/france-bleu-toulouse', 'lecteur_commun_json/timeline-13147'),
        'fbtouraine': (u'France Bleu Touraine (Tours)', 'player/station/france-bleu-touraine', 'lecteur_commun_json/timeline-13149'),
        'fbvaucluse': (u'France Bleu Vaucluse (Avignon)', 'player/station/france-bleu-vaucluse', 'lecteur_commun_json/timeline-13151'),
    }

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            if split_path == [u'francebleu']:
                for _id, item in sorted(self._RADIOS.iteritems()):
                    if _id.startswith('fb'):
                        yield Collection([_id], iter(item).next())
            elif len(split_path) == 0:
                for _id, item in sorted(self._RADIOS.iteritems()):
                    if not _id.startswith('fb'):
                        yield Collection([_id], iter(item).next())
                yield Collection([u'francebleu'], u'France Bleu')
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

        title, player_url, json_url = self._RADIOS[radio.id]
        radio.title = title
        radio.description = title
        radio_name = radio.id if not radio.id.startswith('fb') else 'francebleu'
        url = self.browser.get_radio_url(radio_name, player_url)

        self.fillobj(radio, ('current', ))
        radio.streams = [create_stream(url), create_stream(url, False)]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            title, player_url, json_url = self._RADIOS[radio.id]
            radio_name = radio.id if not radio.id.startswith('fb') else 'francebleu'
            artist, title = self.browser.get_current(radio_name, json_url)
            if not radio.current or radio.current is NotLoaded:
                radio.current = StreamInfo(0)
            radio.current.what = title
            radio.current.who = artist
        return radio

    OBJECTS = {Radio: fill_radio}
