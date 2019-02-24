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
import itertools


class MarmitonTest(BackendTest):
    MODULE = 'marmiton'

    def test_recipe(self):
        recipes = list(itertools.islice(self.backend.iter_recipes('fondue'), 0, 20))
        for recipe in recipes:
            full_recipe = self.backend.get_recipe(recipe.id)
            assert full_recipe.instructions
            assert full_recipe.ingredients
            assert full_recipe.title
            # assert full_recipe.preparation_time (not always filled)
