# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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


def enum(**enums):
    _values = list(enums.values())
    _keys = list(enums.keys())
    _items = list(enums.items())
    _types = list((type(value) for value in enums.values()))
    _index = {(value if not isinstance(value, dict) else next(iter(value.values()))): i
              for i, value in enumerate(enums.values())}

    enums['keys'] = _keys
    enums['values'] = _values
    enums['items'] = _items
    enums['index'] = _index
    enums['types'] = _types
    return type('Enum', (), enums)


FORMATS = enum(HTTP_MP4=u'HBBTV', HLS=u'M3U8', RTMP=u'RTMP', HLS_MOBILE=u'MOBILE')

LANG = enum(FRENCH={u'label': u'French', u'webservice': u'F', u'site': u'fr', u'version': u'1', u'title': u'titleFR'},
            GERMAN={u'label': u'German', u'webservice': u'D', u'site': u'de', u'version': u'1', u'title': u'titleDE'})

CONCERT = enum(CLASSIQUE={u'id': u'CLA', u'label': u'Classique'},
               ACTUELLE={u'id': u'MUA', u'label': u'Musiques actuelles'},
               OPERA={u'id': u'OPE', u'label': u'Opera'},
               JAZZ={u'id': u'JAZ', u'label': u'Jazz'},
               MONDE={u'id': u'MUD', u'label': u'Musiques du monde'},
               SCENE={u'id': u'ADS', u'label': u'Arts de la scène'},
               COLLECTION={u'id': u'collections_ARS', u'label': u'Collections'},
               PLAYLIST={u'id': u'playlists_ARS', u'label': u'Playlists'})

CINEMA = enum(FILM={u'id': u'FLM', u'label': u'Films'},
              CLASSIQUES={u'id': u'MCL', u'label': u'Les grands du 7e art'},
              COURT_METRAGES={u'id': u'CMG', u'label': u'Courts métrages'},
              FILM_MUETS={u'id': u'CMU', u'label': u'Films muets'},
              ACTU={u'id': u'ACC', u'label': u'Actualité du cinéma'},
              COLLECTION={u'id': u'collections_CIN', u'label': u'Collections'},
              MAGAZINE={u'id': u'magazines_CIN', u'label': u'Émissions'})

SERIE = enum(SERIES={u'id': u'SES', u'label': u'Séries'},
             FICTIONS={u'id': u'FIC', u'label': u'Fictions'},
             HUMOUR={u'id': u'CHU', u'label': u'Courts humoristiques'},
             COLLECTION={u'id': u'collections_SER', u'label': u'Collections'})

POP = enum(POP={u'id': u'POP', u'label': u'Culture pop'},
           ART={u'id': u'ART', u'label': u'Arts'},
           IDE={u'id': u'IDE', u'label': u'Idées'},
           COLLECTION={u'id': u'collections_CPO', u'label': u'Collections'},
           MAGAZINE={u'id': u'magazines_CPO', u'label': u'Émissions'})

SCIENCE = enum(POP={u'id': u'SAN', u'label': u'Médecine et santé'},
               EEN={u'id': u'ENN', u'label': u'Environnement et nature'},
               TEC={u'id': u'TEC', u'label': u'Technologies et innovations'},
               ENB={u'id': u'ENB', u'label': u'En bref'},
               COLLECTION={u'id': u'collections_SCI', u'label': u'Collections'},
               MAGAZINE={u'id': u'magazines_SCI', u'label': u'Émissions'})

VOYAGE = enum(NEA={u'id': u'NEA', u'label': u'Nature et animaux'},
              EVA={u'id': u'EVA', u'label': u'Evasion'},
              ATA={u'id': u'ATA', u'label': u'A table !'},
              VIA={u'id': u'VIA', u'label': u'Vies d\'ailleurs'},
              COLLECTION={u'id': u'collections_DEC', u'label': u'Collections'},
              MAGAZINE={u'id': u'magazines_DEC', u'label': u'Émissions'})

HISTOIRE = enum(XXE={u'id': u'XXE', u'label': u'XXe siècle'},
                CIV={u'id': u'CIV', u'label': u'Civilisations'},
                LGP={u'id': u'LGP', u'label': u'Les grands personnages'},
                COLLECTION={u'id': u'collections_DEC', u'label': u'Collections'})

SITE = enum(PROGRAM={u'id': u'program', u'label': u'Arte Programs'},
            CREATIVE={u'id': u'creative', u'label': u'Arte Creative'},
            GUIDE={u'id': u'guide', u'label': u'Arte Guide TV'},
            CONCERT={u'id': u'concert', u'label': u'Arte Concert videos', u'enum': CONCERT},
            CINEMA={u'id': u'cinema', u'label': u'Arte Cinema', u'enum': CINEMA},
            SERIE={u'id': u'series-et-fictions', u'label': u'Arte CreativeSéries et fictions', u'enum': SERIE},
            POP={u'id': u'culture-et-pop', u'label': u'Culture et pop', u'enum': POP},
            SCIENCE={u'id': u'sciences', u'label': u'Sciences', u'enum': SCIENCE},
            VOYAGE={u'id': u'voyages-et-decouvertes', u'label': u'Voyages et découvertes', u'enum': VOYAGE},
            HISTOIRE={u'id': u'histoire', u'label': u'Histoire', u'enum': HISTOIRE})

QUALITY = enum(HD={'label': u'SQ', 'order': 3},
               MD={'label': u'EQ', 'order': 2},
               SD={'label': u'MQ', 'order': 1},
               LD={'label': u'LQ', 'order': 0},
               XD={'label': u'XQ', 'order': 4},)

VERSION_VIDEO = enum(VOSTA={u'label': u'Original version subtitled (German)', LANG.GERMAN.get('label'): u'3'},
                     VOSTF={u'label': u'Original version subtitled (French)', LANG.FRENCH.get('label'): u'3'},
                     VASTA={u'label': u'Translated version (German)',
                            LANG.GERMAN.get('label'): u'1', LANG.FRENCH.get('label'): u'2'},
                     VFSTF={u'label': u'Translated version (French)',
                            LANG.FRENCH.get('label'): u'1', LANG.GERMAN.get('label'): u'2'},
                     VASTMA={u'label': u'Deaf version (German)', LANG.GERMAN.get('label'): u'8'},
                     VFSTMF={u'label': u'Deaf version (French)', LANG.FRENCH.get('label'): u'8'})


def get_site_enum_by_id(id):
    for s in SITE.values:
        if s.get('id') == id:
            return s
    return
