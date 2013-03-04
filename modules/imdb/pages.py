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


from weboob.capabilities.cinema import Person
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage

from datetime import datetime


__all__ = ['MoviePage','PersonPage','MovieCrewPage']


class MoviePage(BasePage):
    ''' Page describing a movie, only used to go on the MovieCrewPage
    '''
    def iter_persons(self,id):
        self.browser.location('http://www.imdb.com/title/%s/fullcredits'%id)
        assert self.browser.is_on_page(MovieCrewPage)
        for p in self.browser.page.iter_persons():
            yield p

    def iter_persons_ids(self,id):
        self.browser.location('http://www.imdb.com/title/%s/fullcredits'%id)
        assert self.browser.is_on_page(MovieCrewPage)
        for p in self.browser.page.iter_persons_ids():
            yield p


class MovieCrewPage(BasePage):
    ''' Page listing all the persons related to a movie
    '''
    def iter_persons(self):
        tables = self.parser.select(self.document.getroot(),'table.cast')
        if len(tables) > 0:
            table = tables[0]
            tds = self.parser.select(table,'td.nm')
            for td in tds:
                id = td.find('a').attrib.get('href','').strip('/').split('/')[-1]
                yield self.browser.get_person(id)

    def iter_persons_ids(self):
        tables = self.parser.select(self.document.getroot(),'table.cast')
        if len(tables) > 0:
            table = tables[0]
            tds = self.parser.select(table,'td.nm')
            for td in tds:
                id = td.find('a').attrib.get('href','').strip('/').split('/')[-1]
                yield id


class PersonPage(BasePage):
    ''' Page giving informations about a person
    It is used to build a Person instance and to get the movie list related to a person
    '''
    def get_person(self,id):
        name = NotAvailable
        biography = NotAvailable
        birth_place = NotAvailable
        birth_date = NotAvailable
        death_date = NotAvailable
        real_name = NotAvailable
        gender = NotAvailable
        nationality = NotAvailable
        td_overview = self.parser.select(self.document.getroot(),'td#overview-top',1)
        descs = self.parser.select(td_overview,'span[itemprop=description]')
        if len(descs) > 0:
            biography = descs[0].text
        rname_block = self.parser.select(td_overview,'div.txt-block h4.inline')
        if len(rname_block) > 0 and "born" in rname_block[0].text.lower():
            links = self.parser.select(rname_block[0].getparent(),'a')
            for a in links:
                href = a.attrib.get('href','').strip()
                if href == 'bio':
                    real_name = a.text.strip()
                elif 'birth_place' in href:
                    birth_place = a.text.lower().strip()
        names = self.parser.select(td_overview,'h1[itemprop=name]')
        if len(names) > 0:
            name = names[0].text.strip()
        times = self.parser.select(td_overview,'time[itemprop=birthDate]')
        if len(times) > 0:
            time = times[0].attrib.get('datetime','').split('-')
            if len(time) == 2:
                time.append('1')
            elif len(time) == 1:
                time.append('1')
                time.append('1')
            birth_date = datetime(int(time[0]),int(time[1]),int(time[2]))
        dtimes = self.parser.select(td_overview,'time[itemprop=deathDate]')
        if len(dtimes) > 0:
            dtime = dtimes[0].attrib.get('datetime','').split('-')
            if len(dtime) == 2:
                dtime.append('1')
            elif len(dtime) == 1:
                dtime.append('1')
                dtime.append('1')
            death_date = datetime(int(dtime[0]),int(dtime[1]),int(dtime[2]))

        person = Person(id,name)
        person.real_name       = real_name
        person.birth_date      = birth_date
        person.death_date      = death_date
        person.birth_place     = birth_place
        person.gender          = gender
        person.nationality     = nationality
        person.biography       = biography
        person.roles           = {}
        return person

    def iter_movies(self,person_id):
        for movie_div in self.parser.select(self.document.getroot(),'div[class~=filmo-row]'):
            a = self.parser.select(movie_div,'b a',1)
            id = a.attrib.get('href','').strip('/').split('/')[-1]
            yield self.browser.get_movie(id)

    def iter_movies_ids(self,person_id):
        for movie_div in self.parser.select(self.document.getroot(),'div[class~=filmo-row]'):
            a = self.parser.select(movie_div,'b a',1)
            id = a.attrib.get('href','').strip('/').split('/')[-1]
            yield id
