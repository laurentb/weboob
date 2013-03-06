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

from __future__ import with_statement

import sys
from datetime import datetime

from weboob.capabilities.cinema import ICapCinema
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Cineoob']


class MovieInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'original_title', 'release_date', 'other_titles', 'duration', 'description', 'note', 'roles', 'country')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.original_title, self.NC)
        result += 'ID: %s\n' % obj.fullid
        if obj.release_date != NotAvailable:
            result += 'Released: %s\n' % obj.release_date.strftime('%Y-%m-%d')
        result += 'Country: %s\n' % obj.country
        if obj.duration != NotAvailable:
            result += 'Duration: %smin\n' % obj.duration
        result += 'Note: %s\n' % obj.note
        if obj.roles:
            result += '\n%sRelated persons%s\n' % (self.BOLD, self.NC)
            for role,lpersons in obj.roles.items():
                result += ' -- %s\n' % role
                for name in lpersons:
                    result += '   * %s\n' % name
        if obj.other_titles:
            result += '\n%sOther titles%s\n' % (self.BOLD, self.NC)
            for t in obj.other_titles:
                result += ' * %s\n' % t
        if obj.description != NotAvailable:
            result += '\n%sDescription%s\n' % (self.BOLD, self.NC)
            result += '%s'%obj.description
        return result


class MovieListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'original_title', 'release_date', 'duration', 'note')

    def get_title(self, obj):
        return obj.original_title

    def get_description(self, obj):
        date_str = ''
        if obj.release_date != NotAvailable and obj.release_date != NotLoaded:
            date_str = 'released: %s, '%obj.release_date.strftime('%Y-%m-%d')
        duration = ''
        if obj.duration != NotAvailable and obj.duration != NotLoaded:
            duration = 'duration: %smin, '%obj.duration
        note = ''
        if obj.note != NotAvailable and obj.note != NotLoaded:
            note = 'note: %s, '%obj.note
        return ('%s %s %s' % (date_str, note, duration)).strip(', ')

def yearsago(years, from_date=None):
    if from_date is None:
        from_date = datetime.now()
    try:
        return from_date.replace(year=from_date.year - years)
    except:
        # Must be 2/29
        assert from_date.month == 2 and from_date.day == 29
        return from_date.replace(month=2, day=28,
                                 year=from_date.year-years)

def num_years(begin, end=None):
    if end is None:
        end = datetime.now()
    num_years = int((end - begin).days / 365.25)
    if begin > yearsago(num_years, end):
        return num_years - 1
    else:
        return num_years

class PersonInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'real_name', 'birth_date', 'birth_place', 'gender', 'nationality', 'short_biography', 'roles')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.name, self.NC)
        result += 'ID: %s\n' % obj.fullid
        if obj.real_name != NotAvailable:
            result += 'Real name: %s\n' % obj.real_name
        if obj.birth_place != NotAvailable:
            result += 'Birth place: %s\n' % obj.birth_place
        if obj.birth_date != NotAvailable:
            result += 'Birth date: %s\n' % obj.birth_date.strftime('%Y-%m-%d')
            if obj.death_date != NotAvailable:
                age = num_years(obj.birth_date,obj.death_date)
                result += 'Death date: %s at %s years old\n' % (obj.death_date.strftime('%Y-%m-%d'),age)
            else:
                age = num_years(obj.birth_date)
                result += 'Age: %s\n' % age
        if obj.gender != NotAvailable:
            result += 'Gender: %s\n' % obj.gender
        if obj.nationality != NotAvailable:
            result += 'Nationality: %s\n' % obj.nationality
        if obj.roles:
            result += '\n%sRelated movies%s\n' % (self.BOLD, self.NC)
            for role,lmovies in obj.roles.items():
                result += ' -- %s\n' % role
                for movie in lmovies:
                    result += '   * %s\n' % movie
        if obj.short_biography != NotAvailable:
            result += '\n%sBiography%s\n' % (self.BOLD, self.NC)
            result += '%s'%obj.short_biography
        return result


class PersonListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'real_name', 'birth_date', 'nationality', 'gender')

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        age = ''
        if obj.birth_date != NotAvailable and obj.death_date == NotAvailable:
            age = 'age: %s'%num_years(obj.birth_date)
        gender = ''
        if obj.gender != NotAvailable:
            gender = 'gender: %s, '%obj.gender
        real_name = ''
        if obj.real_name != NotAvailable:
            real_name = 'real name: %s, '%obj.real_name
        nationality = ''
        if obj.nationality != NotAvailable:
            nationality = 'nationality: %s, '%obj.nationality
        return ('%s%s%s%s' % (real_name, age, nationality, gender)).strip(' ,')


class Cineoob(ReplApplication):
    APPNAME = 'cineoob'
    VERSION = '0.f'
    COPYRIGHT = 'Copyright(C) 2013 Julien Veyssier'
    DESCRIPTION = "Console application allowing to search for movies and persons on various cinema databases " \
                  ", list persons related to a movie, list movies related to a person and list common movies " \
                  "of two persons."
    SHORT_DESCRIPTION = "search movies and persons around cinema"
    CAPS = ICapCinema
    EXTRA_FORMATTERS = {'movie_list': MovieListFormatter,
                        'movie_info': MovieInfoFormatter,
                        'person_list': PersonListFormatter,
                        'person_info': PersonInfoFormatter,
                       }
    COMMANDS_FORMATTERS = {'search_movie':    'movie_list',
                           'info_movie':      'movie_info',
                           'search_person':   'person_list',
                           'info_person':     'person_info',
                           'casting':         'person_list',
                           'filmography':     'movie_list',
                           'movies_in_common':'movie_list',
                           'persons_in_common':'person_list'
                          }
    ROLE_LIST = ['actor','director','writer','composer','producer']

    def complete_filmography(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 3:
            return self.ROLE_LIST

    def complete_casting(self, text, line, *ignored):
        return self.complete_filmography(text,line,ignored)

    def do_movies_in_common(self, line):
        """
        movies_in_common  person_ID  person_ID

        Get the list of common movies between two persons.
        """
        id1, id2 = self.parse_command_args(line, 2, 1)

        person1 = self.get_object(id1, 'get_person')
        if not person1:
            print >>sys.stderr, 'Person not found: %s' % id1
            return 3
        person2 = self.get_object(id2, 'get_person')
        if not person2:
            print >>sys.stderr, 'Person not found: %s' % id2
            return 3

        initial_count = self.options.count
        self.options.count = None

        lid1 = []
        for backend, id in self.do('iter_person_movies_ids', person1.id):
            lid1.append(id)
        self.flush()
        lid2 = []
        for backend, id in self.do('iter_person_movies_ids', person2.id):
            lid2.append(id)
        self.flush()
        self.options.count = initial_count
        inter = list(set(lid1) & set(lid2))
        for common in inter:
            movie = self.get_object(common, 'get_movie')
            self.cached_format(movie)
        self.flush()

    def do_persons_in_common(self, line):
        """
        persons_in_common  movie_ID  movie_ID

        Get the list of common persons between two movies.
        """
        id1, id2 = self.parse_command_args(line, 2, 1)
        self.flush()

        movie1 = self.get_object(id1, 'get_movie')
        if not movie1:
            print >>sys.stderr, 'Movie not found: %s' % id1
            return 3
        movie2 = self.get_object(id2, 'get_movie')
        if not movie2:
            print >>sys.stderr, 'Movie not found: %s' % id2
            return 3

        initial_count = self.options.count
        self.options.count = None

        lid1 = []
        for backend, id in self.do('iter_movie_persons_ids', movie1.id):
            lid1.append(id)
        self.flush()
        lid2 = []
        for backend, id in self.do('iter_movie_persons_ids', movie2.id):
            lid2.append(id)
        self.flush()
        self.options.count = initial_count
        inter = list(set(lid1) & set(lid2))
        for common in inter:
            person = self.get_object(common, 'get_person')
            self.cached_format(person)
        self.flush()

    def do_info_movie(self, id):
        """
        info_movie  movie_ID

        Get information about a movie.
        """
        # TODO correct core to call fillobj when get_object is called
        #movie = self.get_object(id, 'get_movie',['duration'])
        movie = None
        _id, backend = self.parse_id(id)
        for _backend, result in self.do('get_movie', _id, backends=backend):
            if result:
                backend = _backend
                movie = result

        if not movie:
            print >>sys.stderr, 'Movie not found: %s' % id
            return 3

        backend.fillobj(movie, ('description','duration'))

        self.start_format()
        self.format(movie)
        self.flush()

    def do_info_person(self, id):
        """
        info_person  person_ID

        Get information about a person.
        """
        # TODO correct core to call fillobj when get_object is called
        #person = self.get_object(id, 'get_person')
        person = None
        _id, backend = self.parse_id(id)
        for _backend, result in self.do('get_person', _id, backends=backend):
            if result:
                backend = _backend
                person = result

        if not person:
            print >>sys.stderr, 'Person not found: %s' % id
            return 3

        backend.fillobj(person, ('birth_date','short_biography'))

        self.start_format()
        self.format(person)
        self.flush()

    def do_search_movie(self, pattern):
        """
        search_movie  [PATTERN]

        Search movies.
        """
        self.change_path([u'search movies'])
        if not pattern:
            pattern = None

        self.start_format(pattern=pattern)
        for backend, movie in self.do('iter_movies', pattern=pattern):
            self.cached_format(movie)
        self.flush()

    def do_search_person(self, pattern):
        """
        search_person  [PATTERN]

        Search persons.
        """
        self.change_path([u'search persons'])
        if not pattern:
            pattern = None

        self.start_format(pattern=pattern)
        for backend, person in self.do('iter_persons', pattern=pattern):
            self.cached_format(person)
        self.flush()

    def do_casting(self, line):
        """
        casting  movie_ID  [ROLE]

        List persons related to a movie.
        If ROLE is given, filter by ROLE
        """
        movie_id, role = self.parse_command_args(line, 2, 1)

        movie = self.get_object(movie_id, 'get_movie')
        if not movie:
            print >>sys.stderr, 'Movie not found: %s' % id
            return 3

        for backend, person in self.do('iter_movie_persons', movie.id, role):
            self.cached_format(person)
        self.flush()

    def do_filmography(self, line):
        """
        filmography  person_ID  [ROLE]

        List movies of a person.
        If ROLE is given, filter by ROLE
        """
        person_id, role = self.parse_command_args(line, 2, 1)

        person = self.get_object(person_id, 'get_person')
        if not person:
            print >>sys.stderr, 'Person not found: %s' % id
            return 3

        for backend, movie in self.do('iter_person_movies', person.id, role):
            self.cached_format(movie)
        self.flush()

    def do_biography(self, person_id):
        """
        biography  person_ID

        Show the complete biography of a person.
        """
        person = self.get_object(person_id, 'get_person')
        if not person:
            print >>sys.stderr, 'Person not found: %s' % id
            return 3

        for backend, bio in self.do('get_person_biography', person.id):
            print '%s :\n\n%s' % (person.name,bio)
        if bio != NotAvailable:
            self.flush()
