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
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.cinema import Movie
from weboob.tools.json import json

from .pages import MoviePage, PersonPage, MovieCrewPage

from datetime import datetime

__all__ = ['ImdbBrowser']


class ImdbBrowser(BaseBrowser):
    DOMAIN = 'www.imdb.com'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'http://www.imdb.com/title/tt[0-9]*/*': MoviePage,
        'http://www.imdb.com/title/tt[0-9]*/fullcredits.*': MovieCrewPage,
        'http://www.imdb.com/name/nm.*': PersonPage,
        }

    def iter_movies(self, pattern):
        res = self.readurl('http://www.imdb.com/xml/find?json=1&nr=1&tt=on&q=%s' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for cat in ['title_exact','title_popular','title_approx']:
            if jres.has_key(cat):
                for m in jres[cat]:
                    yield self.get_movie(m['id'])

    def iter_persons(self, pattern):
        res = self.readurl('http://www.imdb.com/xml/find?json=1&nr=1&nm=on&q=%s' % pattern.encode('utf-8'))
        jres = json.loads(res)
        for cat in ['name_exact','name_popular','name_approx']:
            if jres.has_key(cat):
                for p in jres[cat]:
                    yield self.get_person(p['id'])

    def get_movie(self, id):
        res = self.readurl('http://imdbapi.org/?id=%s&type=json&plot=simple&episode=1&lang=en-US&aka=full&release=simple&business=0&tech=0' % id )
        jres = json.loads(res)

        title = NotAvailable
        duration = NotAvailable
        release_date = NotAvailable
        description = NotAvailable
        country = NotAvailable
        note = NotAvailable
        other_titles = []
        roles = {}

        title = jres['title']
        if jres.has_key('runtime'):
            duration = int(jres['runtime'][0].split()[0])
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
            country = ''
            for c in jres['country']:
                country += '%s, '%c
            country = country[:-2]
        if jres.has_key('plot_simple'):
            description = jres['plot_simple']
        if jres.has_key('rating') and jres.has_key('rating_count'):
            note = "%s/10 (%s votes)"%(jres['rating'],jres['rating_count'])
        for r in ['actor','director','writer']:
            if jres.has_key('%ss'%r):
                roles['%s'%r] = list(jres['%ss'%r])


        movie = Movie(id,title.strip())
        movie.other_titles    = other_titles
        movie.release_date    = release_date
        movie.duration        = duration
        movie.description     = description
        movie.country         = country
        movie.note            = note
        movie.roles           = roles
        return movie


        #self.location('http://www.imdb.com/title/%s' % id)
        #assert self.is_on_page(MoviePage)
        #return self.page.get_movie(id)

    def get_person(self, id):
        self.location('http://www.imdb.com/name/%s' % id)
        assert self.is_on_page(PersonPage)
        return self.page.get_person(id)

    def iter_movie_persons(self, movie_id):
        self.location('http://www.imdb.com/title/%s' % movie_id)
        assert self.is_on_page(MoviePage)
        return self.page.iter_persons(movie_id)

    def iter_person_movies(self, person_id):
        self.location('http://www.imdb.com/name/%s' % person_id)
        assert self.is_on_page(PersonPage)
        return self.page.iter_movies(person_id)
