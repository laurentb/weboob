# -*- coding: utf-8 -*-

# Copyright(C) 2018      Phyks (Lucas Verney)
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

from __future__ import unicode_literals
import itertools


from weboob.tools.test import BackendTest


class JournaldesfemmesTest(BackendTest):
    MODULE = 'journaldesfemmes'

    def test_recipe(self):
        recipes = list(itertools.islice(self.backend.iter_recipes('fondue'), 0, 20))
        self.assertGreater(len(recipes), 0)
        for recipe in recipes:
            self.assertTrue(recipe.id)
            self.assertTrue(recipe.url)
            self.assertTrue(recipe.title)
            self.assertTrue(recipe.picture.thumbnail.url)
            self.assertTrue(recipe.preparation_time)
            self.assertGreaterEqual(recipe.cooking_time, 0)

            full_recipe = self.backend.get_recipe(recipe.id)
            self.assertTrue(full_recipe.id)
            self.assertTrue(full_recipe.title)
            self.assertTrue(full_recipe.short_description)
            self.assertTrue(full_recipe.author)
            self.assertTrue(full_recipe.ingredients)
            self.assertTrue(full_recipe.picture.thumbnail.url)
            self.assertTrue(full_recipe.picture.url)
            self.assertTrue(full_recipe.preparation_time)
            self.assertGreaterEqual(full_recipe.cooking_time, 0)
            self.assertTrue(full_recipe.instructions)
            self.assertTrue(full_recipe.nb_person)
