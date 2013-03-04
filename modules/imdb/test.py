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

from weboob.tools.test import BackendTest

#from random import choice

class ImdbTest(BackendTest):
    BACKEND = 'imdb'

    def test_movie(self):
        movies = list(self.backend.iter_movies('spiderman'))
        for movie in movies:
            assert movie.id
            assert movie.original_title
            assert movie.release_date
    
    def test_persons(self):
        persons = list(self.backend.iter_persons('robert'))
        for person in persons:
            assert person.id
            assert person.name
            assert person.birth_date
