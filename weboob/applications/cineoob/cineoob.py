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
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter
from weboob.core import CallErrors


__all__ = ['Cineoob']


class MovieInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'original_title', 'release_date', 'other_titles', 'duration', 'description', 'note', 'awards','roles')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.original_title, self.NC)
        result += 'ID: %s\n' % obj.fullid
        result += 'Other titles: %s\n' % obj.other_titles
        result += 'Released: %s\n' % obj.release_date
        result += 'Duration: %d\n' % obj.duration
        result += 'Note: %s\n' % obj.note
        if obj.roles:
            result += '\n%sRelated persons%s\n' % (self.BOLD, self.NC)
            for role,lpersons in obj.roles.items():
                result += ' -- %s\n' % role
                for person in lpersons:
                    result += '   * %s\n' % person.name
        if obj.awards:
            result += '\n%sAwards%s\n' % (self.BOLD, self.NC)
            for a in obj.awards:
                result += ' * %s\n' % a
        result += '\n%sDescription%s\n' % (self.BOLD, self.NC)
        result += obj.description
        return result


class MovieListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'original_title', 'release_date', 'duration', 'note')

    def get_title(self, obj):
        return obj.original_title

    def get_description(self, obj):
        return 'Released: %s   (note: %d, duration: %d)' % (obj.release_date, obj.note, obj.duration)

def num_years(begin, end=None):
    if end is None:
        end = datetime.now()
    num_years = int((end - begin).days / 365.25)
    if begin > yearsago(num_years, end):
        return num_years - 1
    else:
        return num_years

class PersonInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'real_name', 'birth_date', 'birth_place', 'gender', 'nationality', 'biography', 'awards','roles')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.name, self.NC)
        result += 'ID: %s\n' % obj.fullid
        result += 'Real name: %s\n' % obj.real_name
        result += 'Birth date: %s\n' % obj.birth_date
        age = num_years(obj.birth_date)
        result += 'Age: %s\n' % obj.age
        result += 'Birth place: %d\n' % obj.birth_place
        result += 'Gender: %s\n' % obj.gender
        result += 'Nationality: %s\n' % obj.nationality
        if obj.roles:
            result += '\n%sRelated movies%s\n' % (self.BOLD, self.NC)
            for role,lmovies in obj.roles.items():
                result += ' -- %s\n' % role
                for movie in lmovies:
                    result += '   * %s\n' % movie.original_title
        if obj.awards:
            result += '\n%sAwards%s\n' % (self.BOLD, self.NC)
            for a in obj.awards:
                result += ' * %s\n' % a
        result += '\n%Biography%s\n' % (self.BOLD, self.NC)
        result += obj.biography
        return result


class PersonListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'name', 'real_name', 'birth_date', 'nationality', 'gender')

    def get_title(self, obj):
        return obj.name

    def get_description(self, obj):
        age = num_years(obj.birth_date)
        return 'Real name: %s   (age: %d, nationality: %s, gender: %s)' % (obj.real_name, age, obj.nationality, obj.gender)


class Cineoob(ReplApplication):
    APPNAME = 'cineoob'
    VERSION = '0.f'
    COPYRIGHT = 'Copyright(C) 2013 Julien Veyssier'
    DESCRIPTION = "Console application allowing to search for movies and persons on various cinema databases " \
                  ", list persons related to a movie and list movies related to a person."
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
                           'filmography':     'movie_list'
                          }

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info_movie(self, id):
        """
        info_movie ID

        Get information about a movie.
        """

        movie = self.get_object(id, 'get_movie')
        if not movie:
            print >>sys.stderr, 'Movie not found: %s' % id
            return 3

        self.start_format()
        self.format(movie)
        self.flush()

    def do_info_person(self, id):
        """
        info_person ID

        Get information about a person.
        """

        person = self.get_object(id, 'get_person')
        if not person:
            print >>sys.stderr, 'Person not found: %s' % id
            return 3

        self.start_format()
        self.format(person)
        self.flush()

    def do_search_movie(self, pattern):
        """
        search [PATTERN]

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
        search [PATTERN]

        Search persons.
        """
        self.change_path([u'search persons'])
        if not pattern:
            pattern = None

        self.start_format(pattern=pattern)
        for backend, person in self.do('iter_persons', pattern=pattern):
            self.cached_format(person)
        self.flush()

    def do_casting(self, movie_id):
        """
        casting movie_id

        List persons related to a movie.
        """
        self.change_path([u'casting'])
        for backend, person in self.do('iter_movie_persons', movie_id):
            self.cached_format(person)
        self.flush()

    def do_filmography(self, person_id):
        """
        filmography person_id

        List movies of a person.
        """
        self.change_path([u'filmography'])
        for backend, movie in self.do('iter_person_movies', person_id):
            self.cached_format(movie)
        self.flush()
