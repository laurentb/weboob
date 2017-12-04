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

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Regexp, CleanText, Format, Env, CleanDecimal, Eval
from weboob.browser.filters.json import Dict
from weboob.capabilities.recipe import Recipe, Comment
from weboob.tools.json import json
import re


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """
    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = "//div[@class='recipe-results ']/a"

        def next_page(self):
            return CleanText('//nav/ul/li[@class="next-page"]/a/@href', default="")(self)

        class item(ItemElement):
            klass = Recipe
            obj_id = Regexp(CleanText('./@href'),
                            '/recettes/recette_(.*).aspx')
            obj_title = CleanText('./div/h4')
            obj_short_description = Format('%s. %s',
                                           CleanText('./div/div[@class="recipe-card__description"]',
                                                     replace=[(u'Ingrédients : ', ''), ('...', '')]),
                                           CleanText('./div/div[@class="recipe-card__duration"]'))


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """

    @method
    class get_recipe(ItemElement):
        klass = Recipe

        def parse(self, el):
            json_content = CleanText(u'//script[@type="application/ld+json"]',
                                     replace=[('//<![CDATA[ ', ''),
                                              (' //]]>', '')])(self)
            self.el = json.loads(json_content)

        obj_id = Env('id')
        obj_title = Dict('name')
        obj_ingredients = Dict('recipeIngredient')

        obj_thumbnail_url = Dict('image')
        obj_picture_url = Dict('image')

        def obj_instructions(self):
            str = Dict('recipeInstructions')(self)
            return re.sub(r'(\d+\.)', r'\n\1', str)

        obj_preparation_time = Eval(int, CleanDecimal(Dict('prepTime')))
        obj_cooking_time = Eval(int, CleanDecimal(Dict('cookTime')))

        def obj_nb_person(self):
            return [Dict('recipeYield')(self)]


class CommentsPage(HTMLPage):
    """ Page which contains a comments
    """

    @method
    class get_comments(ListElement):
        item_xpath = '//div[@class="commentaire"]/div/table/tr'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Comment

            obj_author = CleanText('./td/div[@class="txtCommentaire"]/div[1]')
            obj_rate = CleanText('./td/div[@class="bulle"]')

            def obj_text(self):
                return CleanText('./td/div[@class="txtCommentaire"]')(self)

            obj_id = CleanText('./td/div[@class="txtCommentaire"]/div[1]')
