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


from weboob.capabilities.cinema import Person, Movie
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.browser import BasePage

from datetime import datetime
import re


__all__ = ['PersonPage', 'MovieCrewPage', 'BiographyPage', 'FilmographyPage', 'ReleasePage']


class ReleasePage(BasePage):
    ''' Page containing releases of a movie
    '''
    def get_movie_releases(self, country_filter):
        result = unicode()
        links = self.parser.select(self.document.getroot(), 'table#release_dates a')
        for a in links:
            href = a.attrib.get('href', '')

            # XXX: search() could raise an exception
            if href.strip('/').split('/')[0] == 'calendar' and\
                    (country_filter is None or re.search('region=([a-zA-Z]+)&', href).group(1).lower() == country_filter):
                country = a.text
                td_date = self.parser.select(a.getparent().getparent().getparent(), 'td')[1]
                date_links = self.parser.select(td_date, 'a')
                if len(date_links) > 1:
                    date = date_links[1].attrib.get('href', '').strip('/').split('/')[-1]
                    date += '-'+date_links[0].attrib.get('href', '').strip('/').split('/')[-1]
                else:
                    date = unicode(self.parser.select(a.getparent().getparent().getparent(), 'td')[1].text_content())
                result += '%s : %s\n' % (country, date)
        if result == u'':
            result = NotAvailable
        else:
            result = result.strip()
        return result


class BiographyPage(BasePage):
    ''' Page containing biography of a person
    '''
    def get_biography(self):
        bio = unicode()
        tn = self.parser.select(self.document.getroot(), 'div#tn15content', 1)
        # we only read paragraphs, titles and links
        for ch in tn.getchildren():
            if ch.tag in ['p', 'h5', 'a']:
                bio += '%s\n\n' % ch.text_content().strip()
        if bio == u'':
            bio = NotAvailable
        return bio


class MovieCrewPage(BasePage):
    ''' Page listing all the persons related to a movie
    '''
    def iter_persons(self, role_filter=None):
        if (role_filter is None or (role_filter is not None and role_filter == 'actor')):
            tables = self.parser.select(self.document.getroot(), 'table.cast_list')
            if len(tables) > 0:
                table = tables[0]
                tds = self.parser.select(table, 'td.itemprop')

                for td in tds:
                    id = td.find('a').attrib.get('href', '').strip('/').split('/')[1]
                    name = unicode(td.find('a').text)
                    char_name = unicode(self.parser.select(td.getparent(), 'td.character', 1).text_content())
                    person = Person(id, name)
                    person.short_description = char_name
                    person.real_name = NotLoaded
                    person.birth_place = NotLoaded
                    person.birth_date = NotLoaded
                    person.death_date = NotLoaded
                    person.gender = NotLoaded
                    person.nationality = NotLoaded
                    person.short_biography = NotLoaded
                    person.roles = NotLoaded
                    person.thumbnail_url = NotLoaded
                    yield person

        for gloss_link in self.parser.select(self.document.getroot(), 'table[cellspacing="1"] h5 a'):
            role = gloss_link.attrib.get('name', '').rstrip('s')
            if (role_filter is None or (role_filter is not None and role == role_filter)):
                tbody = gloss_link.getparent().getparent().getparent().getparent()
                for line in self.parser.select(tbody, 'tr')[1:]:
                    for a in self.parser.select(line, 'a'):
                        role_detail = NotAvailable
                        href = a.attrib.get('href', '')
                        if '/name/nm' in href:
                            id = href.strip('/').split('/')[-1]
                            name = unicode(a.text)
                        if 'glossary' in href:
                            role_detail = unicode(a.text)
                        person = Person(id, name)
                        person.short_description = role_detail
                        yield person
                            # yield self.browser.get_person(id)

    def iter_persons_ids(self):
        tables = self.parser.select(self.document.getroot(), 'table.cast_list')
        if len(tables) > 0:
            table = tables[0]
            tds = self.parser.select(table, 'td.itemprop')
            for td in tds:
                id = td.find('a').attrib.get('href', '').strip('/').split('/')[1]
                yield id


class PersonPage(BasePage):
    ''' Page informing about a person
    It is used to build a Person instance and to get the movie list related to a person
    '''
    def get_person(self, id):
        name = NotAvailable
        short_biography = NotAvailable
        short_description = NotAvailable
        birth_place = NotAvailable
        birth_date = NotAvailable
        death_date = NotAvailable
        real_name = NotAvailable
        gender = NotAvailable
        thumbnail_url = NotAvailable
        roles = {}
        nationality = NotAvailable
        td_overview = self.parser.select(self.document.getroot(), 'td#overview-top', 1)
        descs = self.parser.select(td_overview, 'span[itemprop=description]')
        if len(descs) > 0:
            short_biography = unicode(descs[0].text)
        rname_block = self.parser.select(td_overview, 'div.txt-block h4.inline')
        if len(rname_block) > 0 and "born" in rname_block[0].text.lower():
            links = self.parser.select(rname_block[0].getparent(), 'a')
            for a in links:
                href = a.attrib.get('href', '').strip()
                if href == 'bio':
                    real_name = unicode(a.text.strip())
                elif 'birth_place' in href:
                    birth_place = unicode(a.text.lower().strip())
        names = self.parser.select(td_overview, 'h1 span[itemprop=name]')
        if len(names) > 0:
            name = unicode(names[0].text.strip())
        times = self.parser.select(td_overview, 'time[itemprop=birthDate]')
        if len(times) > 0:
            time = times[0].attrib.get('datetime', '').split('-')
            if len(time) == 3 and int(time[0]) >= 1900:
                birth_date = datetime(int(time[0]), int(time[1]), int(time[2]))
        dtimes = self.parser.select(td_overview, 'time[itemprop=deathDate]')
        if len(dtimes) > 0:
            dtime = dtimes[0].attrib.get('datetime', '').split('-')
            if len(dtime) == 3 and int(dtime[0]) >= 1900:
                death_date = datetime(int(dtime[0]), int(dtime[1]), int(dtime[2]))
        img_thumbnail = self.parser.select(self.document.getroot(), 'td#img_primary img')
        if len(img_thumbnail) > 0:
            thumbnail_url = unicode(img_thumbnail[0].attrib.get('src', ''))

        # go to the filmography page
        self.browser.location('http://www.imdb.com/name/%s/filmotype' % id)
        assert self.browser.is_on_page(FilmographyPage)
        roles = self.browser.page.get_roles()

        person = Person(id, name)
        person.real_name = real_name
        person.birth_date = birth_date
        person.death_date = death_date
        person.birth_place = birth_place
        person.gender = gender
        person.nationality = nationality
        person.short_biography = short_biography
        person.short_description = short_description
        person.roles = roles
        person.thumbnail_url = thumbnail_url
        return person


class FilmographyPage(BasePage):
    ''' Page of detailed filmography of a person, sorted by type of role
    This page is easier to parse than the main person page filmography
    '''
    def iter_movies_ids(self):
        for role_div in self.parser.select(self.document.getroot(), 'div.filmo'):
            for a in self.parser.select(role_div, 'ol > li > a'):
                id = a.attrib.get('href', '').strip('/').split('/')[-1]
                if id.startswith('tt'):
                    yield id

    def get_roles(self):
        roles = {}
        for role_div in self.parser.select(self.document.getroot(), 'div.filmo'):
            role = self.parser.select(role_div, 'h5 a', 1).text.replace(':', '')
            roles[role] = []
            for a in self.parser.select(role_div, 'ol > li > a'):
                id = a.attrib.get('href', '').strip('/').split('/')[-1]
                if id.startswith('tt'):
                    if '(' in a.tail and ')' in a.tail:
                        between_p = a.tail.split(')')[0].split('(')[1]
                    else:
                        between_p = '????'
                    roles[role].append('(%s) %s' % (between_p, a.text))
        return roles

    def iter_movies(self, role_filter=None):
        for role_div in self.parser.select(self.document.getroot(), 'div.filmo'):
            role = self.parser.select(role_div, 'h5 a', 1).text.replace(':', '')
            if (role_filter is None or (role_filter is not None and role.lower().strip() == role_filter))\
                    and role != 'In Development':
                for a in self.parser.select(role_div, 'ol > li > a'):
                    id = a.attrib.get('href', '').strip('/').split('/')[-1]
                    if id.startswith('tt'):
                        title = unicode(a.text)
                        role_detail = NotAvailable
                        if len(a.tail) > 0:
                            role_detail = unicode(' '.join(a.tail.replace('..', '').split()))
                        movie = Movie(id, title)
                        movie.short_description = role_detail
                        yield movie
