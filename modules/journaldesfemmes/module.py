# -*- coding: utf-8 -*-

# Copyright(C) 2018      Phyks (Lucas Verney)
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

from __future__ import unicode_literals


from weboob.tools.backend import Module
from weboob.capabilities.recipe import CapRecipe, Recipe

from .browser import JournaldesfemmesBrowser


__all__ = ['JournaldesfemmesModule']


class JournaldesfemmesModule(Module, CapRecipe):
    NAME = 'journaldesfemmes'
    DESCRIPTION = 'journaldesfemmes website'
    MAINTAINER = 'Phyks (Lucas Verney)'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'

    BROWSER = JournaldesfemmesBrowser

    def get_recipe(self, _id):
        """
        Get a recipe object from an ID.

        :param _id: ID of recipe
        :type _id: str
        :rtype: :class:`Recipe`
        """
        return self.browser.get_recipe(_id)

    def iter_recipes(self, pattern):
        """
        Search recipes and iterate on results.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`Recipe`]
        """
        return self.browser.search_recipes(pattern)

    def fill_recipe(self, recipe, fields):
        if 'nb_person' in fields or 'instructions' in fields:
            recipe = self.browser.get_recipe(recipe.id, recipe)

        if 'comments' in fields:
            recipe.comments = list(self.browser.get_comments(recipe.id))

        return recipe

    OBJECTS = {Recipe: fill_recipe}
