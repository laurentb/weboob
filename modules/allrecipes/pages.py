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


from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import ItemElement, DictElement, method
from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.browser.filters.standard import Env, Format, Join
from weboob.browser.filters.json import Dict


class HomePage(HTMLPage):
    pass


class ResultsPage(JsonPage):
    @pagination
    @method
    class iter_recipes(DictElement):

        item_xpath = 'recipes'

        def next_page(self):
            return Dict('links/next/href', default=None)(self.page.doc)

        class item(ItemElement):
            klass = Recipe

            obj_id = Dict('recipeID')
            obj_title = Dict('title')
            obj_short_description = Dict('description')


class RecipePage(JsonPage):
    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('_id')
        obj_title = Dict('title')
        obj_short_description = Dict('description')
        obj_preparation_time = Dict('prepMinutes')
        obj_cooking_time = Dict('cookMinutes')

        def obj_nb_person(self):
            nb_pers = u'%s' % Dict('servings', default='')(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            ingredients = []
            for el in Dict('ingredients')(self):
                ing = Format('%s (%s gramm)',
                             Dict('displayValue'),
                             Dict('grams'))(el)
                ingredients.append(ing)
            return ingredients

        def obj_instructions(self):
            ins = [Dict('displayValue')(el) for el in Dict('directions')(self)]
            return Join('\n * ', ins, addBefore=' * ', addAfter='\n')(self)

        obj_thumbnail_url = Dict('photo/photoDetailUrl')
        obj_picture_url = Dict('photo/photoDetailUrl')

    @method
    class get_comments(DictElement):
        item_xpath = 'topReviews'

        class item(ItemElement):
            klass = Comment

            obj_author = Dict('submitter/name')
            obj_rate = Dict('rating')
            obj_text = Dict('text')
            obj_id = Dict('reviewID')
