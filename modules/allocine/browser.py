# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import base64
import hashlib
import time
from datetime import date, datetime, timedelta

from weboob.browser.browsers import APIBrowser
from weboob.browser.profiles import Android
from weboob.capabilities.base import NotAvailable, NotLoaded, find_object
from weboob.capabilities.calendar import CATEGORIES, STATUS, TRANSP, BaseCalendarEvent
from weboob.capabilities.cinema import Movie, Person
from weboob.capabilities.collection import Collection
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo
from weboob.tools.compat import unicode, urlencode

__all__ = ['AllocineBrowser']


class AllocineBrowser(APIBrowser):
    PROFILE = Android()

    PARTNER_KEY = '100043982026'
    SECRET_KEY = '29d185d98c984a359e6e6f26a0474269'

    def __do_request(self, method, params):
        params["sed"] = time.strftime('%Y%m%d', time.localtime())
        params["sig"] = base64.b64encode(
            hashlib.sha1(
                self.SECRET_KEY +
                urlencode(params)
            ).digest()
        )

        return self.request(
            'http://api.allocine.fr/rest/v3/{}'.format(method),
            params=params
        )

    def iter_movies(self, pattern):
        params = [('partner', self.PARTNER_KEY),
                  ('q', pattern),
                  ('format', 'json'),
                  ('filter', 'movie')]

        jres = self.__do_request('search', params)
        if jres is None:
            return
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
                  ('q', pattern),
                  ('format', 'json'),
                  ('filter', 'person')]

        jres = self.__do_request('search', params)
        if jres is None:
            return
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

        jres = self.__do_request('movie', params)
        if jres is not None:
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
            note = u'%s/5 (%s votes)' % (jres['statistics']['userRating'], jres['statistics']['userReviewCount'])
        if 'castMember' in jres:
            for cast in jres['castMember']:
                if cast['activity']['$'] not in roles:
                    roles[cast['activity']['$']] = []
                person_to_append = (u'%s' % cast['person']['code'], cast['person']['name'])
                roles[cast['activity']['$']].append(person_to_append)

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

        jres = self.__do_request('person', params)
        if jres is not None:
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
                movie_to_append = (u'%s' % (m['movie']['code']), u'(%s) %s' % (pyear, m['movie']['originalTitle']))
                roles[m['activity']['$']].append(movie_to_append)

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

        jres = self.__do_request('movie', params)
        if jres is not None:
            if 'movie' in jres:
                jres = jres['movie']
            else:
                return
        else:
            return
        if 'castMember' in jres:
            for cast in jres['castMember']:
                if (role_filter is None or
                   (role_filter is not None and cast['activity']['$'].lower().strip() == role_filter.lower().strip())):
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

        jres = self.__do_request('filmography', params)
        if jres is not None:
            if 'person' in jres:
                jres = jres['person']
            else:
                return
        else:
            return
        for m in jres['participation']:
            if (role_filter is None or
               (role_filter is not None and m['activity']['$'].lower().strip() == role_filter.lower().strip())):
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

        jres = self.__do_request('filmography', params)
        if jres is not None:
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

        jres = self.__do_request('movie', params)
        if jres is not None:
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
        if country == 'fr':
            return self.get_movie(id).release_date

    def get_person_biography(self, id):
        params = [('partner', self.PARTNER_KEY),
                  ('code', id),
                  ('profile', 'large'),
                  ('mediafmt', 'mp4-lc'),
                  ('filter', 'movie'),
                  ('striptags', 'biography,biographyshort'),
                  ('format', 'json')]

        jres = self.__do_request('person', params)
        if jres is not None:
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

    def get_categories_movies(self, category):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('mediafmt', 'mp4'),
                  ('filter', category)
                  ]
        result = self.__do_request('movielist', params)
        if result is None:
            return
        for movie in result['feed']['movie']:
            if 'trailer' not in movie or 'productionYear' not in movie:
                continue
            yield self.parse_movie(movie)

    def get_categories_videos(self, category):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('mediafmt', 'mp4'),
                  ('filter', category)
                  ]
        result = self.__do_request('videolist', params)
        if result is None:
            return
        if 'feed' in result and 'media' in result['feed']:
            for episode in result['feed']['media']:
                if 'title' in episode:
                    yield self.parse_video(episode, category)

    def parse_video(self, _video, category):
        video = BaseVideo(u'%s#%s' % (_video['code'], category))
        video.title = unicode(_video['title'])
        video._video_code = unicode(_video['code'])
        video.ext = u'mp4'
        if 'runtime' in _video:
            video.duration = timedelta(seconds=int(_video['runtime']))
        if 'description' in _video:
            video.description = unicode(_video['description'])
        renditions = sorted(_video['rendition'],
                            key=lambda x: 'bandwidth' in x and x['bandwidth']['code'],
                            reverse=True)
        video.url = unicode(max(renditions, key=lambda x: 'bandwidth' in x)['href'])
        return video

    def parse_movie(self, movie):
        video = BaseVideo(u'%s#%s' % (movie['code'], 'movie'))
        video.title = unicode(movie['trailer']['name'])
        video._video_code = unicode(movie['trailer']['code'])
        video.ext = u'mp4'
        if 'poster' in movie:
            video.thumbnail = Thumbnail(movie['poster']['href'])
            video.thumbnail.url = unicode(movie['poster']['href'])
        tdate = movie['release']['releaseDate'].split('-')
        day = 1
        month = 1
        year = 1901
        if len(tdate) > 2:
            year = int(tdate[0])
            month = int(tdate[1])
            day = int(tdate[2])

        video.date = date(year, month, day)
        if 'userRating' in movie['statistics']:
            video.rating = movie['statistics']['userRating']
        elif 'pressRating' in movie['statistics']:
            video.rating = movie['statistics']['pressRating'] * 2
        video.rating_max = 5
        if 'synopsis' in movie:
            video.description = unicode(movie['synopsis'].replace('<p>', '').replace('</p>', ''))
        elif 'synopsisShort' in movie:
            video.description = unicode(movie['synopsisShort'].replace('<p>', '').replace('</p>', ''))
        if 'castingShort' in movie:
            if 'directors' in movie['castingShort']:
                video.author = unicode(movie['castingShort']['directors'])
        if 'runtime' in movie:
            video.duration = timedelta(seconds=int(movie['runtime']))
        return video

    def get_movie_from_id(self, _id):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('mediafmt', 'mp4'),
                  ('filter', 'movie'),
                  ('code', _id),
                  ]
        result = self.__do_request('movie', params)
        if result is None:
            return
        return self.parse_video(result['movie'])

    def get_video_from_id(self, _id, category):
        return find_object(self.get_categories_videos(category), id=u'%s#%s' % (_id, category))

    def get_video_url(self, code):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('mediafmt', 'mp4'),
                  ('code', code),
                  ('profile', 'large'),
                  ]
        result = self.__do_request('media', params)
        if result is None:
            return
        renditions = sorted(result['media']['rendition'],
                            key=lambda x: 'bandwidth' in x and x['bandwidth']['code'],
                            reverse=True)
        return max(renditions, key=lambda x: 'bandwidth' in x)['href']

    def get_emissions(self, basename):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('filter', 'acshow'),
                  ]
        result = self.__do_request('termlist', params)
        if result is None:
            return
        for emission in result['feed']['term']:
            yield Collection([basename, unicode(emission['nameShort'])], unicode(emission['$']))

    def search_events(self, query):
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('zip', query.city)
                  ]

        if query.summary:
            movie = self.iter_movies(query.summary).next()
            params.append(('movie', movie.id))

        result = self.__do_request('showtimelist', params)
        if result is None:
            return

        for event in self.create_event(result):
            if (not query.end_date or event.start_date <= query.end_date)\
               and event.start_date >= query.start_date:
                yield event

    def get_event(self, _id):
        split_id = _id.split('#')
        params = [('partner', self.PARTNER_KEY),
                  ('format', 'json'),
                  ('theaters', split_id[0]),
                  ('zip', split_id[1]),
                  ('movie', split_id[2]),
                  ]

        result = self.__do_request('showtimelist', params)
        if result is None:
            return

        for event in self.create_event(result):
            if event.id.split('#')[-1] == split_id[-1]:
                event.description = self.get_movie(split_id[2]).pitch
                return event

    def create_event(self, data):
        sequence = 1
        transp = TRANSP.TRANSPARENT
        status = STATUS.CONFIRMED
        category = CATEGORIES.CINE

        if 'theaterShowtimes' not in data['feed']:
            return

        for items in data['feed']['theaterShowtimes']:
            cinema = items['place']['theater']
            city = unicode(cinema['city'])
            location = u'%s, %s' % (cinema['name'], cinema['address'])
            postalCode = cinema['postalCode']
            cinemaCode = cinema['code']
            for show in items['movieShowtimes']:
                summary = unicode(show['onShow']['movie']['title'])
                movieCode = show['onShow']['movie']['code']
                for jour in show['scr']:
                    tdate = jour['d'].split('-')
                    year = int(tdate[0])
                    month = int(tdate[1])
                    day = int(tdate[2])
                    for seance in jour['t']:
                        ttime = seance['$'].split(':')
                        heure = int(ttime[0])
                        minute = int(ttime[1])
                        start_date = datetime(year=year, month=month, day=day,
                                              hour=heure, minute=minute)

                        seanceCode = seance['code']
                        _id = u'%s#%s#%s#%s' % (cinemaCode, postalCode, movieCode, seanceCode)
                        event = BaseCalendarEvent()
                        event.id = _id
                        event.sequence = sequence
                        event.transp = transp
                        event.status = status
                        event.category = category
                        event.city = city
                        event.location = location
                        event.start_date = start_date
                        event.summary = summary
                        event.timezone = u'Europe/Paris'
                        yield event
