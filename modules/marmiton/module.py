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

from weboob.capabilities.recipe import CapRecipe, Recipe
from weboob.tools.backend import Module
from weboob.tools.compat import quote_plus

from .browser import MarmitonBrowser


__all__ = ['MarmitonModule']


class MarmitonModule(Module, CapRecipe):
    NAME = 'marmiton'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.4'
    DESCRIPTION = u'Marmiton French recipe website'
    LICENSE = 'AGPLv3+'
    BROWSER = MarmitonBrowser

    def get_recipe(self, id):
        return self.browser.get_recipe(id)

    def iter_recipes(self, pattern):
        return self.browser.iter_recipes(quote_plus(pattern.encode('utf-8')))

    def fill_recipe(self, recipe, fields):
        if 'nb_person' in fields or 'instructions' in fields or 'thumbnail_url' in fields:
            recipe = self.browser.get_recipe(recipe.id, recipe)
        return recipe

    OBJECTS = {
        Recipe: fill_recipe,
    }
