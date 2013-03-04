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
from weboob.tools.json import json

from .pages import MoviePage, PersonPage, MovieCrewPage


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
        # the api leads to a json result or the html movie page if there is only one result
        self.location('http://www.imdb.com/xml/find?json=1&tt=on&q=%s' % pattern.encode('utf-8'))
        if self.is_on_page(MoviePage):
            yield self.page.get_movie()
        else:
            res = self.readurl('http://www.imdb.com/xml/find?json=1&tt=on&q=%s' % pattern.encode('utf-8'))
            jres = json.loads(res)
            for restype,mlist in jres.items():
                for m in mlist:
                    yield self.get_movie(m['id'])

    def iter_persons(self, pattern):
        # the api leads to a json result or the html movie page if there is only one result
        self.location('http://www.imdb.com/xml/find?json=1&nm=on&q=%s' % pattern.encode('utf-8'))
        if self.is_on_page(PersonPage):
            yield self.page.get_person()
        else:
            res = self.readurl('http://www.imdb.com/xml/find?json=1&nm=on&q=%s' % pattern.encode('utf-8'))
            jres = json.loads(res)
            for restype,plist in jres.items():
                for p in plist:
                    yield self.get_person(p['id'])

    def get_movie(self, id):
        self.location('http://www.imdb.com/title/%s' % id)
        assert self.is_on_page(MoviePage)
        return self.page.get_movie(id)

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
