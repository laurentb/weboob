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


class SupertoinetteTest(BackendTest):
    MODULE = 'supertoinette'

    def test_recipe(self):
        recipes = self.backend.iter_recipes('fondue')
        for recipe in recipes:
            full_recipe = self.backend.get_recipe(recipe.id)
            assert full_recipe.instructions
            assert full_recipe.ingredients
            assert full_recipe.title
