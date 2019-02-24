# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.tools.test import BackendTest


class ImdbTest(BackendTest):
    MODULE = 'imdb'

    def test_search_movie(self):
        movies = list(self.backend.iter_movies('spiderman'))
        assert len(movies) > 0
        for movie in movies:
            assert movie.id

    def test_get_movie(self):
        movie = self.backend.get_movie('tt0079980')
        assert movie
        assert movie.id
        assert movie.original_title

    def test_search_person(self):
        persons = list(self.backend.iter_persons('dewaere'))
        assert len(persons) > 0
        for person in persons:
            assert person.id

    def test_get_person(self):
        person = self.backend.get_person('nm0223033')
        assert person
        assert person.id
        assert person.name
        assert person.birth_date

    def test_movie_persons(self):
        persons = list(self.backend.iter_movie_persons('tt0079980'))
        assert len(persons) > 0
        for person in persons:
            assert person.id
            assert person.name
            assert person.short_description

    def test_person_movies(self):
        movies = list(self.backend.iter_person_movies('nm0223033'))
        assert len(movies) > 0
        for movie in movies:
            assert movie.id
            assert movie.original_title

    def test_get_person_biography(self):
        bio = self.backend.get_person_biography('nm0223033')
        assert bio != ''
        assert bio is not None

    def test_get_movie_releases(self):
        rel = self.backend.get_movie_releases('tt0079980', 'fr')
        assert rel != ''
        assert rel is not None
        assert rel == 'France : 25 April 1979'

    def test_iter_person_movies_ids(self):
        movies_ids = list(self.backend.iter_person_movies_ids('nm0223033'))
        assert len(movies_ids) > 0
        for movie_id in movies_ids:
            assert movie_id

    def test_iter_movie_persons_ids(self):
        persons_ids = list(self.backend.iter_movie_persons_ids('tt0079980'))
        assert len(persons_ids) > 0
        for person_id in persons_ids:
            assert person_id
