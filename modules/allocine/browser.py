# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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


import HTMLParser
from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.cinema import Movie, Person
from weboob.tools.json import json

from .pages import PersonPage, MovieCrewPage, BiographyPage, FilmographyPage, ReleasePage

from datetime import datetime

__all__ = ['AllocineBrowser']


class AllocineBrowser(BaseBrowser):
    DOMAIN = 'api.allocine.fr'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    #PAGES = {
    #    'http://www.imdb.com/title/tt[0-9]*/fullcredits.*': MovieCrewPage,
    #    'http://www.imdb.com/title/tt[0-9]*/releaseinfo.*': ReleasePage,
    #    'http://www.imdb.com/name/nm[0-9]*/*': PersonPage,
    #    'http://www.imdb.com/name/nm[0-9]*/bio.*': BiographyPage,
    #    'http://www.imdb.com/name/nm[0-9]*/filmo.*': FilmographyPage,
    #}

    def iter_movies(self, pattern):
        res = self.readurl('http://api.allocine.fr/rest/v3/search?partner=YW5kcm9pZC12M3M&filter=movie&q=%s&format=json' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for m in jres['feed']['movie']:
            tdesc = u''
            if 'title' in m:
                tdesc += '%s' % m['title']
            if 'productionYear' in m:
                tdesc += ' ; %s' % m['productionYear']
            elif 'release' in m:
                tdesc += ' ; %s' % m['release']['releaseDate']
            short_description = tdesc.strip('; ')
            movie = Movie(m['code'], unicode(m['originalTitle']))
            movie.other_titles = NotLoaded
            movie.release_date = NotLoaded
            movie.duration = NotLoaded
            movie.short_description = short_description
            movie.pitch = NotLoaded
            movie.country = NotLoaded
            movie.note = NotLoaded
            movie.roles = NotLoaded
            movie.all_release_dates = NotLoaded
            movie.thumbnail_url = NotLoaded
            yield movie

    def iter_persons(self, pattern):
        res = self.readurl('http://api.allocine.fr/rest/v3/search?partner=YW5kcm9pZC12M3M&filter=person&q=%s&format=json' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for p in jres['feed']['person']:
            thumbnail_url = NotAvailable
            if 'picture' in p:
                thumbnail_url = unicode(p['picture']['href'])
            person = Person(p['code'], unicode(p['name']))
            desc = u''
            if 'birthDate' in p:
                desc += '(%s), ' % p['birthDate']
            if 'activity' in p:
                for a in p['activity']:
                    desc += '%s, ' % a['$']
            person.real_name = NotLoaded
            person.birth_place = NotLoaded
            person.birth_date = NotLoaded
            person.death_date = NotLoaded
            person.gender = NotLoaded
            person.nationality = NotLoaded
            person.short_biography = NotLoaded
            person.short_description = desc.strip(', ')
            person.roles = NotLoaded
            person.thumbnail_url = thumbnail_url
            yield person

    def get_movie(self, id):
        res = self.readurl(
                'http://api.allocine.fr/rest/v3/movie?partner=YW5kcm9pZC12M3M&code=%s&profile=large&mediafmt=mp4-lc&format=json&filter=movie&striptags=synopsis,synopsisshort' % id)
        if res is not None:
            jres = json.loads(res)['movie']
        else:
            return None
        title = NotAvailable
        duration = NotAvailable
        release_date = NotAvailable
        pitch = NotAvailable
        country = NotAvailable
        note = NotAvailable
        short_description = NotAvailable
        thumbnail_url = NotAvailable
        other_titles = []
        genres = []
        roles = {}

        if 'originalTitle' not in jres:
            return
        title = unicode(jres['originalTitle'].strip())
        if 'picture' in jres:
            thumbnail_url = unicode(jres['picture']['href'])
        if 'genre' in jres:
            for g in jres['genre']:
                genres.append(g['$'])
        if 'runtime' in jres:
            nbsecs = jres['runtime']
            duration = nbsecs / 60
        #if 'also_known_as' in jres:
        #    for other_t in jres['also_known_as']:
        #        if 'country' in other_t and 'title' in other_t:
        #            other_titles.append('%s : %s' % (other_t['country'], htmlparser.unescape(other_t['title'])))
        if 'release' in jres:
            dstr = str(jres['release']['releaseDate'])
            tdate = dstr.split('-')
            day = 1
            month = 1
            year = 1901
            if len(tdate) > 2:
                year = int(tdate[0])
                month = int(tdate[1])
                day = int(tdate[2])
            release_date = datetime(year, month, day)
        if 'nationality' in jres:
            country = u''
            for c in jres['nationality']:
                country += '%s, ' % c['$']
            country = country.strip(', ')
        if 'synopsis' in jres:
            pitch = unicode(jres['synopsis'])
        if 'statistics' in jres and 'userRating' in jres['statistics']:
            note = u'%s/10 (%s votes)' % (jres['statistics']['userRating'], jres['statistics']['userReviewCount'])
        if 'castMember' in jres:
            for cast in jres['castMember']:
                if cast['activity']['$'] not in roles:
                    roles[cast['activity']['$']] = []
                roles[cast['activity']['$']].append(cast['person']['name'])

        movie = Movie(id, title)
        movie.other_titles = other_titles
        movie.release_date = release_date
        movie.duration = duration
        movie.genres = genres
        movie.pitch = pitch
        movie.country = country
        movie.note = note
        movie.roles = roles
        movie.short_description = short_description
        movie.all_release_dates = NotLoaded
        movie.thumbnail_url = thumbnail_url
        return movie

    def get_person(self, id):
        try:
            self.location('http://www.imdb.com/name/%s' % id)
        except BrowserHTTPNotFound:
            return
        assert self.is_on_page(PersonPage)
        return self.page.get_person(id)

    def get_person_biography(self, id):
        self.location('http://www.imdb.com/name/%s/bio' % id)
        assert self.is_on_page(BiographyPage)
        return self.page.get_biography()

    def iter_movie_persons(self, movie_id, role):
        self.location('http://www.imdb.com/title/%s/fullcredits' % movie_id)
        assert self.is_on_page(MovieCrewPage)
        for p in self.page.iter_persons(role):
            yield p

    def iter_person_movies(self, person_id, role):
        self.location('http://www.imdb.com/name/%s/filmotype' % person_id)
        assert self.is_on_page(FilmographyPage)
        return self.page.iter_movies(role)

    def iter_person_movies_ids(self, person_id):
        self.location('http://www.imdb.com/name/%s/filmotype' % person_id)
        assert self.is_on_page(FilmographyPage)
        for movie in self.page.iter_movies_ids():
            yield movie

    def iter_movie_persons_ids(self, movie_id):
        self.location('http://www.imdb.com/title/%s/fullcredits' % movie_id)
        assert self.is_on_page(MovieCrewPage)
        for person in self.page.iter_persons_ids():
            yield person

    def get_movie_releases(self, id, country):
        return
        self.location('http://www.imdb.com/title/%s/releaseinfo' % id)
        assert self.is_on_page(ReleasePage)
        return self.page.get_movie_releases(country)


dict_hex = {'&#xE1;': u'á',
            '&#xE9;': u'é',
            '&#xE8;': u'è',
            '&#xED;': u'í',
            '&#xF1;': u'ñ',
            '&#xF3;': u'ó',
            '&#xFA;': u'ú',
            '&#xFC;': u'ü',
            '&#x26;': u'&',
            '&#x27;': u"'",
            '&#xE0;': u'à',
            '&#xC0;': u'À',
            '&#xE2;': u'â',
            '&#xC9;': u'É',
            '&#xEB;': u'ë',
            '&#xF4;': u'ô',
            '&#xE7;': u'ç'
            }


def latin2unicode(word):
    for key in dict_hex.keys():
        word = word.replace(key, dict_hex[key])
    return unicode(word)
