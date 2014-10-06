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


from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.cinema import Movie, Person
from weboob.deprecated.browser import Browser
from weboob.tools.json import json
import base64
import hashlib
from datetime import datetime
import time
import urllib


__all__ = ['AllocineBrowser']


class AllocineBrowser(Browser):
    DOMAIN = 'api.allocine.fr'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = 'Dalvik/1.6.0 (Linux; U; Android 4.2.2; Nexus 4 Build/JDQ39E)'

    PARTNER_KEY = '100043982026'
    SECRET_KEY = '29d185d98c984a359e6e6f26a0474269'

    def __do_request(self, method, params):
        params_encode = urllib.urlencode(params)

        sed = time.strftime('%Y%m%d', time.localtime())
        sig = base64.b64encode(hashlib.sha1(self.SECRET_KEY + params_encode + '&sed=' + sed).digest())

        query_url = 'http://api.allocine.fr/rest/v3/' + method + '?' + params_encode + '&sed=' + sed + '&sig=' + sig

        return self.readurl(query_url)

    def iter_movies(self, pattern):
        params = [('partner', self.PARTNER_KEY),
                  ('q', pattern.encode('utf-8')),
                  ('format', 'json'),
                  ('filter', 'movie')]

        res = self.__do_request('search', params)
        if res is None:
            return
        jres = json.loads(res)
        if 'movie' not in jres['feed']:
            return
        for m in jres['feed']['movie']:
            tdesc = u''
            if 'title' in m:
                tdesc += '%s' % m['title']
            if 'productionYear' in m:
                tdesc += ' ; %s' % m['productionYear']
            elif 'release' in m:
                tdesc += ' ; %s' % m['release']['releaseDate']
            if 'castingShort' in m and 'actors' in m['castingShort']:
                tdesc += ' ; %s' % m['castingShort']['actors']
            short_description = tdesc.strip('; ')
            thumbnail_url = NotAvailable
            if 'poster' in m:
                thumbnail_url = unicode(m['poster']['href'])
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
            movie.thumbnail_url = thumbnail_url
            yield movie

    def iter_persons(self, pattern):
        params = [('partner', self.PARTNER_KEY),
                  ('q', pattern.encode('utf-8')),
                  ('format', 'json'),
                  ('filter', 'person')]

        res = self.__do_request('search', params)
        if res is None:
            return
        jres = json.loads(res)
        if 'person' not in jres['feed']:
            return
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
        params = [('partner', self.PARTNER_KEY),
                  ('code', id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'synopsis,synopsisshort'),
                  ('format', 'json')]

        res = self.__do_request('movie', params)
        if res is not None:
            jres = json.loads(res)
            if 'movie' in jres:
                jres = jres['movie']
            else:
                return None
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
        if 'poster' in jres:
            thumbnail_url = unicode(jres['poster']['href'])
        if 'genre' in jres:
            for g in jres['genre']:
                genres.append(g['$'])
        if 'runtime' in jres:
            nbsecs = jres['runtime']
            duration = nbsecs / 60
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
        params = [('partner', self.PARTNER_KEY),
                  ('code', id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'biography,biographyshort'),
                  ('format', 'json')]

        res = self.__do_request('person', params)
        if res is not None:
            jres = json.loads(res)
            if 'person' in jres:
                jres = jres['person']
            else:
                return None
        else:
            return None
        name = NotAvailable
        short_biography = NotAvailable
        biography = NotAvailable
        short_description = NotAvailable
        birth_place = NotAvailable
        birth_date = NotAvailable
        death_date = NotAvailable
        real_name = NotAvailable
        gender = NotAvailable
        thumbnail_url = NotAvailable
        roles = {}
        nationality = NotAvailable

        if 'name' in jres:
            name = u''
            if 'given' in jres['name']:
                name += jres['name']['given']
            if 'family' in jres['name']:
                name += ' %s' % jres['name']['family']
        if 'biographyShort' in jres:
            short_biography = unicode(jres['biographyShort'])
        if 'birthPlace' in jres:
            birth_place = unicode(jres['birthPlace'])
        if 'birthDate' in jres:
            df = jres['birthDate'].split('-')
            birth_date = datetime(int(df[0]), int(df[1]), int(df[2]))
        if 'deathDate' in jres:
            df = jres['deathDate'].split('-')
            death_date = datetime(int(df[0]), int(df[1]), int(df[2]))
        if 'realName' in jres:
            real_name = unicode(jres['realName'])
        if 'gender' in jres:
            gcode = jres['gender']
            if gcode == '1':
                gender = u'Male'
            else:
                gender = u'Female'
        if 'picture' in jres:
            thumbnail_url = unicode(jres['picture']['href'])
        if 'nationality' in jres:
            nationality = u''
            for n in jres['nationality']:
                nationality += '%s, ' % n['$']
            nationality = nationality.strip(', ')
        if 'biography' in jres:
            biography = unicode(jres['biography'])
        if 'participation' in jres:
            for m in jres['participation']:
                if m['activity']['$'] not in roles:
                    roles[m['activity']['$']] = []
                pyear = '????'
                if 'productionYear' in m['movie']:
                    pyear = m['movie']['productionYear']
                roles[m['activity']['$']].append(u'(%s) %s' % (pyear, m['movie']['originalTitle']))


        person = Person(id, name)
        person.real_name = real_name
        person.birth_date = birth_date
        person.death_date = death_date
        person.birth_place = birth_place
        person.gender = gender
        person.nationality = nationality
        person.short_biography = short_biography
        person.biography = biography
        person.short_description = short_description
        person.roles = roles
        person.thumbnail_url = thumbnail_url
        return person

    def iter_movie_persons(self, movie_id, role_filter):
        params = [('partner', self.PARTNER_KEY),
                  ('code', movie_id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'synopsis,synopsisshort'),
                  ('format', 'json')]

        res = self.__do_request('movie', params)
        if res is not None:
            jres = json.loads(res)
            if 'movie' in jres:
                jres = jres['movie']
            else:
                return
        else:
            return
        if 'castMember' in jres:
            for cast in jres['castMember']:
                if (role_filter is None or (role_filter is not None and cast['activity']['$'].lower().strip() == role_filter.lower().strip())):
                    id = cast['person']['code']
                    name = unicode(cast['person']['name'])
                    short_description = unicode(cast['activity']['$'])
                    if 'role' in cast:
                        short_description += ', %s' % cast['role']
                    thumbnail_url = NotAvailable
                    if 'picture' in cast:
                        thumbnail_url = unicode(cast['picture']['href'])
                    person = Person(id, name)
                    person.short_description = short_description
                    person.real_name = NotLoaded
                    person.birth_place = NotLoaded
                    person.birth_date = NotLoaded
                    person.death_date = NotLoaded
                    person.gender = NotLoaded
                    person.nationality = NotLoaded
                    person.short_biography = NotLoaded
                    person.roles = NotLoaded
                    person.thumbnail_url = thumbnail_url
                    yield person

    def iter_person_movies(self, person_id, role_filter):
        params = [('partner', self.PARTNER_KEY),
                  ('code', person_id),
                  ('profile', 'medium'),
                  ('filter', 'movie'),
                  ('format', 'json')]

        res = self.__do_request('filmography', params)
        if res is not None:
            jres = json.loads(res)
            if 'person' in jres:
                jres = jres['person']
            else:
                return
        else:
            return
        for m in jres['participation']:
            if (role_filter is None or (role_filter is not None and m['activity']['$'].lower().strip() == role_filter.lower().strip())):
                prod_year = '????'
                if 'productionYear' in m['movie']:
                    prod_year = m['movie']['productionYear']
                short_description = u'(%s) %s' % (prod_year, m['activity']['$'])
                if 'role' in m:
                    short_description += ', %s' % m['role']
                movie = Movie(m['movie']['code'], unicode(m['movie']['originalTitle']))
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

    def iter_person_movies_ids(self, person_id):
        params = [('partner', self.PARTNER_KEY),
                  ('code', person_id),
                  ('profile', 'medium'),
                  ('filter', 'movie'),
                  ('format', 'json')]

        res = self.__do_request('filmography', params)
        if res is not None:
            jres = json.loads(res)
            if 'person' in jres:
                jres = jres['person']
            else:
                return
        else:
            return
        for m in jres['participation']:
            yield unicode(m['movie']['code'])

    def iter_movie_persons_ids(self, movie_id):
        params = [('partner', self.PARTNER_KEY),
                  ('code', movie_id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'synopsis,synopsisshort'),
                  ('format', 'json')]

        res = self.__do_request('movie', params)
        if res is not None:
            jres = json.loads(res)
            if 'movie' in jres:
                jres = jres['movie']
            else:
                return
        else:
            return
        if 'castMember' in jres:
            for cast in jres['castMember']:
                yield unicode(cast['person']['code'])

    def get_movie_releases(self, id, country):
        return

    def get_person_biography(self, id):
        params = [('partner', self.PARTNER_KEY),
                  ('code', id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'biography,biographyshort'),
                  ('format', 'json')]

        res = self.__do_request('person', params)
        if res is not None:
            jres = json.loads(res)
            if 'person' in jres:
                jres = jres['person']
            else:
                return None
        else:
            return None

        biography = NotAvailable
        if 'biography' in jres:
            biography = unicode(jres['biography'])

        return biography
