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


from weboob.capabilities.cinema import Movie, Person
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage

import string
from datetime import datetime


__all__ = ['MoviePage','PersonPage','MovieCrewPage']


class MoviePage(BasePage):
    def get_movie(self,id):
        title = NotAvailable
        duration = NotAvailable
        release_date = NotAvailable
        description = NotAvailable
        td_overview = self.parser.select(self.document.getroot(),'td#overview-top',1)
        for span in self.parser.select(td_overview,'h1.header span[itemprop=name]'):
            if span.attrib.get('class','') == 'itemprop':
                other_titles = span.text
                if title == NotAvailable:
                    title = other_titles
            elif span.attrib.get('class','') == 'title-extra':
                title = span.text
        metas = self.parser.select(td_overview,'meta[itemprop=datePublished]')
        if len(metas) > 0:
            datestrings = metas[0].attrib.get('content','').split('-')
            if len(datestrings) == 2:
                datestrings.append('1')
            release_date = datetime(int(datestrings[0]),int(datestrings[1]),int(datestrings[2]))
        time = self.parser.select(td_overview,'time[itemprop=duration]')
        if len(time) > 0:
            duration = int(time[0].attrib.get('datetime','').strip(string.letters))
        desc = self.parser.select(td_overview,'p[itemprop=description]')
        if len(desc) > 0:
            description = desc[0].text
        movie = Movie(id,title.strip())
        movie.other_titles    = other_titles.strip()
        movie.release_date    = release_date
        movie.duration        = duration
        movie.description     = description
        movie.note            = "10/10"
        movie.awards          = ["aw1","aw2"]
        movie.roles           = {}
        return movie

    def iter_persons(self,id):
        self.browser.location('http://www.imdb.com/title/%s/fullcredits'%id)
        assert self.browser.is_on_page(MovieCrewPage)
        for p in self.browser.page.iter_persons():
            yield p

class MovieCrewPage(BasePage):
    def iter_persons(self):
        tables = self.parser.select(self.document.getroot(),'table.cast')
        if len(tables) > 0:
            table = tables[0]
            tds = self.parser.select(table,'td.nm')
            for td in tds:
                name = td.text_content()
                id = td.find('a').attrib.get('href','').strip('/').split('/')[-1]
                person = Person(id,name)
                person.real_name = NotAvailable
                person.birth_date = NotAvailable
                person.nationality = NotAvailable
                person.biography = NotAvailable
                person.gender = NotAvailable
                yield person


class PersonPage(BasePage):
    def get_person(self,id):
        name = NotAvailable
        biography = NotAvailable
        birth_place = NotAvailable
        birth_date = NotAvailable
        real_name = NotAvailable
        gender = NotAvailable
        nationality = NotAvailable
        td_overview = self.parser.select(self.document.getroot(),'td#overview-top',1)
        descs = self.parser.select(td_overview,'span[itemprop=description]')
        if len(descs) > 0:
            biography = descs[0].text
        names = self.parser.select(td_overview,'h1[itemprop=name]')
        if len(names) > 0:
            name = names[0].text
        times = self.parser.select(td_overview,'time[itemprop=birthDate]')
        if len(times) > 0:
            time = times[0].attrib.get('datetime','').split('-')
            if len(time) == 2:
                time.append('1')
            elif len(time) == 1:
                time.append('1')
                time.append('1')
            birth_date = datetime(int(time[0]),int(time[1]),int(time[2]))

        person = Person(id,name)
        person.real_name       = real_name
        person.birth_date      = birth_date
        person.birth_place     = birth_place
        person.gender          = gender
        person.nationality     = nationality
        person.biography       = biography
        person.awards          = ["aw1","aw2"]
        person.roles           = {}
        return person

    def iter_movies(self,person_id):
        for movie_div in self.parser.select(self.document.getroot(),'div[class~=filmo-row]'):
            a = self.parser.select(movie_div,'b a',1)
            id = a.attrib.get('href','').strip('/').split('/')[-1]
            yield self.browser.get_movie(id)
            #title = a.text
            #movie = Movie(id,title)
            #movie.other_titles    = NotAvailable 
            #movie.release_date    = NotAvailable 
            #movie.duration        = NotAvailable 
            #movie.description     = NotAvailable 
            #movie.note            = NotAvailable 
            #movie.awards          = NotAvailable 
            #movie.roles           = NotAvailable
            #yield movie
