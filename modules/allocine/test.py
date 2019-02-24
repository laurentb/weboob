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
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.calendar import Query, CATEGORIES
from datetime import datetime
import re


class AllocineTest(BackendTest):
    MODULE = 'allocine'

    def test_search_movie(self):
        movies = list(self.backend.iter_movies('usual suspects'))
        assert len(movies) > 0
        for movie in movies:
            assert movie.id

    def test_get_movie(self):
        movie = self.backend.get_movie('5032')
        assert movie
        assert movie.id
        assert movie.original_title

    def test_search_person(self):
        persons = list(self.backend.iter_persons('patrick dewaere'))
        assert len(persons) > 0
        for person in persons:
            assert person.id

    def test_get_person(self):
        person = self.backend.get_person('1115')
        assert person
        assert person.id
        assert person.name
        assert person.birth_date

    def test_movie_persons(self):
        persons = list(self.backend.iter_movie_persons('5032'))
        assert len(persons) > 0
        for person in persons:
            assert person.id
            assert person.name

    def test_person_movies(self):
        movies = list(self.backend.iter_person_movies('1115'))
        assert len(movies) > 0
        for movie in movies:
            assert movie.id
            assert movie.original_title

    def test_get_person_biography(self):
        bio = self.backend.get_person_biography('1115')
        assert bio != ''
        assert bio is not None
        assert re.match(r'^Patrick Dewaere, fils.*', bio)

    def test_get_movie_releases(self):
        rel = self.backend.get_movie_releases('5032', 'fr')
        assert rel != ''
        assert rel is not None

    def test_iter_person_movies_ids(self):
        movies_ids = list(self.backend.iter_person_movies_ids('1115'))
        assert len(movies_ids) > 0
        for movie_id in movies_ids:
            assert movie_id

    def test_iter_movie_persons_ids(self):
        persons_ids = list(self.backend.iter_movie_persons_ids('5032'))
        assert len(persons_ids) > 0
        for person_id in persons_ids:
            assert person_id

    def test_emissions(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'acshow']))
        assert len(l)
        l1 = list(self.backend.iter_resources([BaseVideo], l[0].split_path))
        assert len(l1)
        v = l1[0]
        self.backend.fillobj(v, 'url')
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_interview(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'interview']))
        assert len(l)
        v = l[0]
        self.backend.fillobj(v, 'url')
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_comingsoon(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'comingsoon']))
        assert len(l)
        v = l[0]
        self.backend.fillobj(v, 'url')
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_nowshowing(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'nowshowing']))
        assert len(l)
        v = l[0]
        self.backend.fillobj(v, 'url')
        self.assertTrue(v.url, 'URL for video "%s" not found' % (v.id))

    def test_showtimelist(self):
        query = Query()
        query.city = u'59000'
        query.categories = [CATEGORIES.CINE]
        query.start_date = datetime.now()
        l = self.backend.search_events(query)
        assert len(l)
        e = l[0]
        self.backend.fillobj(e, 'description')
        self.assertTrue(e.description, 'Description of "%s" not found' % (e.id))
        e = self.backend.get_event(e.id)
        self.assertTrue(e.description, 'Description of "%s" not found' % (e.id))
