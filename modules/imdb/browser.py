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


from weboob.tools.browser import BaseBrowser
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.capabilities.cinema import Movie, Person
from weboob.tools.json import json

from .pages import PersonPage, MovieCrewPage, BiographyPage, FilmographyPage

from datetime import datetime

__all__ = ['ImdbBrowser']


class ImdbBrowser(BaseBrowser):
    DOMAIN = 'www.imdb.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://www.imdb.com/title/tt[0-9]*/fullcredits.*': MovieCrewPage,
        'http://www.imdb.com/name/nm[0-9]*/*': PersonPage,
        'http://www.imdb.com/name/nm[0-9]*/bio.*': BiographyPage,
        'http://www.imdb.com/name/nm[0-9]*/filmo.*': FilmographyPage,
        }

    def iter_movies(self, pattern):
        res = self.readurl('http://www.imdb.com/xml/find?json=1&nr=1&tt=on&q=%s' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for cat in ['title_popular','title_exact','title_approx']:
            if jres.has_key(cat):
                for m in jres[cat]:
                    tdesc = unicode(m['title_description'])
                    if '<a' in tdesc and '>' in tdesc:
                        short_description = u'%s %s'%(tdesc.split('<')[0].strip(', '), tdesc.split('>')[1].split('<')[0])
                    else:
                        short_description = tdesc.strip(', ')
                    #movie = self.get_movie(m['id'])
                    movie = Movie(m['id'],unicode(m['title']))
                    movie.other_titles    = NotLoaded
                    movie.release_date    = NotLoaded
                    movie.duration        = NotLoaded
                    movie.short_description = short_description
                    movie.pitch           = NotLoaded
                    movie.country         = NotLoaded
                    movie.note            = NotLoaded
                    movie.roles           = NotLoaded
                    yield movie

    def iter_persons(self, pattern):
        res = self.readurl('http://www.imdb.com/xml/find?json=1&nr=1&nm=on&q=%s' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for cat in ['name_popular','name_exact','name_approx']:
            if jres.has_key(cat):
                for p in jres[cat]:
                    #person = self.get_person(p['id'])
                    person = Person(p['id'],p['name'])
                    person.real_name    = NotLoaded
                    person.birth_place    = NotLoaded
                    person.birth_date     = NotLoaded
                    person.death_date     = NotLoaded
                    person.gender         = NotLoaded
                    person.nationality    = NotLoaded
                    person.short_biography= NotLoaded
                    person.short_description= unicode(p['description'])
                    person.roles          = NotLoaded
                    yield person

    def get_movie(self, id):
        res = self.readurl('http://imdbapi.org/?id=%s&type=json&plot=simple&episode=1&lang=en-US&aka=full&release=simple&business=0&tech=0' % id )
        if res != None:
            jres = json.loads(res)
        else:
            return None

        title = NotAvailable
        duration = NotAvailable
        release_date = NotAvailable
        pitch = NotAvailable
        country = NotAvailable
        note = NotAvailable
        short_description = NotAvailable
        other_titles = []
        roles = {}

        title = unicode(jres['title'].strip())
        if jres.has_key('directors'):
            short_description = ', '.join(jres['directors'])
        if jres.has_key('runtime'):
            dur_str = jres['runtime'][0].split(':')
            if len(dur_str) == 1:
                duration = int(dur_str[0].split()[0])
            else:
                duration = int(dur_str[1].split()[0])
        if jres.has_key('also_known_as'):
            for other_t in jres['also_known_as']:
                if other_t.has_key('country') and other_t.has_key('title'):
                    other_titles.append('%s : %s' % (other_t['country'],other_t['title']))
        if jres.has_key('release_date'):
            dstr = str(jres['release_date'])
            year = int(dstr[:4])
            if year == 0:
                year = 1
            month = int(dstr[4:5])
            if month == 0:
                month = 1
            day = int(dstr[-2:])
            if day == 0:
                day = 1
            release_date = datetime(year,month,day)
        if jres.has_key('country'):
            country = u''
            for c in jres['country']:
                country += '%s, '%c
            country = country[:-2]
        if jres.has_key('plot_simple'):
            pitch = unicode(jres['plot_simple'])
        if jres.has_key('rating') and jres.has_key('rating_count'):
            note = u'%s/10 (%s votes)'%(jres['rating'],jres['rating_count'])
        for r in ['actor','director','writer']:
            if jres.has_key('%ss'%r):
                roles['%s'%r] = list(jres['%ss'%r])

        movie = Movie(id,title)
        movie.other_titles    = other_titles
        movie.release_date    = release_date
        movie.duration        = duration
        movie.pitch           = pitch
        movie.country         = country
        movie.note            = note
        movie.roles           = roles
        movie.short_description= short_description
        return movie

    def get_person(self, id):
        self.location('http://www.imdb.com/name/%s' % id)
        assert self.is_on_page(PersonPage)
        return self.page.get_person(id)

    def get_person_biography(self, id):
        self.location('http://www.imdb.com/name/%s/bio' % id)
        assert self.is_on_page(BiographyPage)
        return self.page.get_biography()

    def iter_movie_persons(self, movie_id, role):
        self.location('http://www.imdb.com/title/%s/fullcredits'%movie_id)
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
        self.location('http://www.imdb.com/title/%s/fullcredits'%movie_id)
        assert self.is_on_page(MovieCrewPage)
        for person in self.page.iter_persons_ids():
            yield person
