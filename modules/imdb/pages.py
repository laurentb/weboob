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
        description = NotAvailable.__unicode__()
        td_overview = self.parser.select(self.document.getroot(),'td#overview-top',1)
        for span in self.parser.select(td_overview,'h1.header span[itemprop=name]'):
            if span.attrib.get('class','') == 'itemprop':
                other_titles = span.text
                if title == NotAvailable:
                    title = other_titles
            elif span.attrib.get('class','') == 'title-extra':
                title = span.text
        meta = self.parser.select(td_overview,'meta[itemprop=datePublished]',1)
        datestrings = meta.attrib.get('content','').split('-')
        if len(datestrings) == 2:
            datestrings.append('1')
        time = self.parser.select(td_overview,'time[itemprop=duration]')
        if len(time) > 0:
            duration = int(time[0].attrib.get('datetime','').strip(string.letters))
        desc = self.parser.select(td_overview,'p[itemprop=description]')
        if len(desc) > 0:
            description = desc[0].text
        movie = Movie(id,title.strip())
        movie.other_titles    = other_titles.strip()
        movie.release_date    = datetime(int(datestrings[0]),int(datestrings[1]),int(datestrings[2]))
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
                person.gender = NotAvailable
                yield person


class PersonPage(BasePage):
    def get_person(self,id):
        person = Person(id,'nameplop')
        person.real_name       = 'rn'
        person.birth_date      = datetime.now()
        person.birth_place     = "place"
        person.gender          = "M"
        person.nationality     = "nn"
        person.biography       = 'bio'
        person.awards          = ["aw1","aw2"]
        person.roles           = {}
        return person

    def iter_movies(self,person_id):
        pass
