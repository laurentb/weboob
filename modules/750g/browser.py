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

from weboob.browser.exceptions import BrowserHTTPNotFound
from weboob.browser import PagesBrowser, URL
from .pages import RecipePage, ResultsPage


__all__ = ['SevenFiftyGramsBrowser']


class SevenFiftyGramsBrowser(PagesBrowser):
    BASEURL = 'https://www.750g.com'

    search = URL('/recettes_(?P<pattern>.*).htm', ResultsPage)
    recipe = URL('/(?P<id>.*).htm', RecipePage)

    def iter_recipes(self, pattern):
        try:
            self.search.go(pattern=pattern.replace(' ', '_'))
        except BrowserHTTPNotFound:
            return []

        if isinstance(self.page, ResultsPage):
            return self.page.iter_recipes()
        return [self.get_recipe_content()]

    def get_recipe(self, id, recipe=None):
        try:
            self.recipe.go(id=id)
            return self.get_recipe_content(recipe)
        except BrowserHTTPNotFound:
            return

    def get_recipe_content(self, recipe=None):
        recipe = self.page.get_recipe(obj=recipe)
        comments = list(self.page.get_comments())
        if comments:
            recipe.comments = comments
        return recipe
