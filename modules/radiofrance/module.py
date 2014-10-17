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
from weboob.capabilities.video import CapVideo
from weboob.capabilities.radio import CapRadio, Radio
from weboob.capabilities.audiostream import BaseAudioStream
from weboob.tools.capabilities.streaminfo import StreamInfo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module

from .browser import RadioFranceBrowser, RadioFranceVideo


__all__ = ['RadioFranceModule']


class RadioFranceModule(Module, CapRadio, CapCollection, CapVideo):
    NAME = 'radiofrance'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '1.1'
    DESCRIPTION = u'Radios of Radio France: Inter, Info, Bleu, Culture, Musique, FIP, Le Mouv\''
    LICENSE = 'AGPLv3+'
    BROWSER = RadioFranceBrowser

    _MP3_URL = u'http://mp3.live.tv-radio.com/%s/all/%s.mp3'
    _MP3_HD_URL = u'http://mp3.live.tv-radio.com/%s/all/%shautdebit.mp3'
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

    _DIRECTJSON_RADIOS = ('lemouv', )
    _LARGEDIRECTJSON_RADIOS = ('fip', )
    _RSS_RADIOS = ('francemusique', )

    def iter_resources(self, objs, split_path):
        if Radio in objs:
            if split_path == [u'francebleu']:
                for _id in sorted(self._RADIOS.iterkeys()):
                    if _id.startswith('fb'):
                        yield self.get_radio(_id)
            elif len(split_path) == 0:
                for _id in sorted(self._RADIOS.iterkeys()):
                    if not _id.startswith('fb'):
                        yield self.get_radio(_id)
                yield Collection([u'francebleu'], u'France Bleu')
            else:
                raise CollectionNotFound(split_path)

    def iter_radios_search(self, pattern):
        for radio in self.iter_resources_flat((Radio, ), []):
            if pattern.lower() in radio.title.lower() or pattern.lower() in radio.description.lower():
                yield radio

    def get_radio(self, radio):
        if not isinstance(radio, Radio):
            radio = Radio(radio)

        if radio.id not in self._RADIOS:
            return None

        title, hd = self._RADIOS[radio.id]
        radio.title = title
        radio.description = title

        if hd:
            url = self._MP3_HD_URL % (radio.id, radio.id)
        else:
            url = self._MP3_URL % (radio.id, radio.id)

        # This should be asked demand, but is required for now as Radioob
        # does not require it.
        self.fillobj(radio, ('current', ))

        stream = BaseAudioStream(0)
        if hd:
            stream.bitrate = 128
        else:
            stream.bitrate = 32
        stream.format = u'mp3'
        stream.title = u'%s kbits/s' % (stream.bitrate)
        stream.url = url
        radio.streams = [stream]
        return radio

    def fill_radio(self, radio, fields):
        if 'current' in fields:
            artist = title = None
            if radio.id in self._PLAYERJS_RADIOS:
                artist, title = self.browser.get_current_playerjs(radio.id)
                if title.endswith(u'par %s' % artist):
                    artist = None
            if radio.id in self._DIRECTJSON_RADIOS:
                dartist, dtitle = self.browser.get_current_direct(radio.id)
                if dartist:
                    artist = dartist
                if dtitle:
                    if title:
                        title = u"%s [%s]" % (dtitle, title)
                    else:
                        title = dtitle
            elif radio.id in self._LARGEDIRECTJSON_RADIOS:
                dartist, dtitle = self.browser.get_current_direct_large(radio.id)
                if dartist:
                    artist = dartist
                if dtitle:
                    title = dtitle
            if radio.id in self._RSS_RADIOS:
                title = self.browser.get_current_rss(radio.id)
            if title:
                if not radio.current or radio.current is NotLoaded:
                    radio.current = StreamInfo(0)
                radio.current.what = title
                radio.current.who = artist
        return radio

    # TODO
    # http://www.franceculture.fr/recherche/key%3DYOURSEARCH%2526type%3Demission
    # http://www.franceinter.fr/recherche/key%3DYOURSEARCH%2526tri%3Dpertinence%2526theme%3Ddefault%2526type%3Demission
    #def search_videos(self, *args, **kwargs):
    #    return []

    def get_video(self, _id):
        with self.browser:
            video = self.browser.get_video(_id)
        return video

    def fill_video(self, video, fields):
        if 'url' in fields:
            with self.browser:
                video.url = unicode(self.browser.get_url(video.id))

        return video

    OBJECTS = {Radio: fill_radio,
               RadioFranceVideo: fill_video}
