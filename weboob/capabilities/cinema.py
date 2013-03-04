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


from .base import IBaseCap, CapBaseObject, DateField, StringField, IntField, Field


__all__ = ['Movie', 'Person', 'ICapCinema']


class Movie(CapBaseObject):
    """
    Movie object.
    """
    original_title  = StringField('Original title of the movie')
    other_titles    = StringField('Titles in other languages')
    release_date    = DateField('Release date of the movie')
    duration        = IntField('Duration of the movie in minutes')
    description     = StringField('Short description of the movie')
    note            = StringField('Notation of the movie')
    awards          = Field('Awards won by the movie',list)
    roles           = Field('Lists of Persons related to the movie indexed by roles',dict)

    def __init__(self, id, original_title):
        CapBaseObject.__init__(self, id)
        self.original_title = original_title


class Person(CapBaseObject):
    """
    Person object.
    """
    name            = StringField('Star name of a person')
    real_name       = StringField('Real name of a person')
    birth_date      = DateField('Birth date of a person')
    birth_place     = StringField('City and country of birth of a person')
    gender          = StringField('Gender of a person')
    nationality     = StringField('Nationality of a person')
    biography       = StringField('Short biography of a person')
    awards          = Field('Awards won by the person',list)
    roles           = Field('Lists of movies related to the person indexed by roles',dict)

    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.name = name


class ICapCinema(IBaseCap):
    """
    Cinema databases.
    """
    def iter_movies(self, pattern):
        """
        Search movies and iterate on results.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`Movies`]
        """
        raise NotImplementedError()

    def get_movie(self, _id):
        """
        Get a movie object from an ID.

        :param _id: ID of movie
        :type _id: str
        :rtype: :class:`Movie`
        """
        raise NotImplementedError()

    def get_movie_persons(self, _id):
        """
        Get the list of persons who are actors in a movie.

        :param _id: ID of movie
        :type _id: str
        :rtype: iter[:class:`Person`]
        """
        raise NotImplementedError()

    def iter_movie_persons(self, _id):
        """
        Get the list of persons who are related to a movie.

        :param _id: ID of movie
        :type _id: str
        :rtype: iter[:class:`Person`]
        """
        raise NotImplementedError()

    def iter_persons(self, pattern):
        """
        Search persons and iterate on results.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`persons`]
        """
        raise NotImplementedError()

    def get_person(self, _id):
        """
        Get a person object from an ID.

        :param _id: ID of person
        :type _id: str
        :rtype: :class:`Person`
        """
        raise NotImplementedError()

    def iter_person_movies(self, _id):
        """
        Get the list of movies related to a person.

        :param _id: ID of person
        :type _id: str
        :rtype: iter[:class:`Movie`]
        """
        raise NotImplementedError()
