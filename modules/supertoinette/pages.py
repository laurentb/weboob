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

from weboob.capabilities.recipe import Recipe
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage, Thumbnail
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.pages import HTMLPage
from weboob.browser.filters.standard import (
    CleanText, Env, Regexp, Type, Join, Eval,
)
from weboob.browser.filters.html import XPath


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """
    @method
    class iter_recipes(ListElement):
        item_xpath = '//div[@id="searchlist"]/ul/li'

        class item(ItemElement):
            klass = Recipe

            def condition(self):
                return Regexp(CleanText('./h3/a/@href'), 'https://www.supertoinette.com/(recette)/\d*/.*',
                              default=None)(self)

            obj_id = Regexp(CleanText('./h3/a/@href'), 'https://www.supertoinette.com/recette/(.*).html', default=None)

            obj_title = CleanText('./h3/a')
            obj_short_description = CleanText('./p')


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """

    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('_id')
        obj_title = CleanText('//h1')
        obj_preparation_time = Type(Regexp(CleanText('//li[@class="time"]/span'), ".* (\d*) min"), type=int)

        obj_cooking_time = Type(Regexp(CleanText('//li[@class="time-cooking"]/span'), ".* (\d*) min"), type=int)

        def obj_nb_person(self):
            nb_pers = Regexp(CleanText('//div[@class="row ingredients"]/div/p'),
                             '.*pour (\d+) personnes', default=0)(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            i = []
            ingredients = XPath('//ul[@class="ingredientsList"]/li',
                                default=[])(self)
            for ingredient in ingredients:
                i.append(CleanText('.')(ingredient))
            return i

        obj_instructions = Join(u'\n- ', '//div[@class="recipe-prepa"]/ol/li', newline=True, addBefore='- ')

        class obj_picture(ItemElement):
            klass = BaseImage

            obj_url = CleanText('//div[has-class("toprecipeImage")]/img/@src', default=NotAvailable)
            obj_thumbnail = Eval(Thumbnail, obj_url)
