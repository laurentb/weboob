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


from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, Type, Filter
from weboob.browser.filters.html import CleanHTML


class Time(Filter):
    def filter(self, el):
        if el:
            if 'h' in el:
                return 60*int(el.split()[0])
            return int(el.split()[0])


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """
    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//li[@data-type="recette"]'

        def next_page(self):
            return CleanText('//li[@class="suivante"]/a/@href')(self)

        class item(ItemElement):
            klass = Recipe
            obj_id = Regexp(CleanText('./div[has-class("text")]/h2/a/@href'),
                            '(.*).htm')
            obj_title = CleanText('./div[has-class("text")]/h2/a')
            obj_thumbnail_url = CleanText('./div[has-class("image")]/a/img[1]/@src')
            obj_short_description = CleanText('./div[has-class("text")]/p')
            obj_author = CleanText('./div[has-class("text")]/h3[@class="auteur"]/a', default=NotAvailable)


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """
    @method
    class get_comments(ListElement):
        item_xpath = '//section[@class="commentaires_liste"]/article'

        class item(ItemElement):
            klass = Comment

            obj_id = CleanText('./@data-id')
            obj_author = CleanText('./div[@class="column"]/p[@class="commentaire_info"]/span')
            obj_text = CleanText('./div[@class="column"]/p[1]')

    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('id')
        obj_title = CleanText('//h1[@class="fn"]')

        def obj_ingredients(self):
            ingredients = []
            for el in self.page.doc.xpath('//section[has-class("recette_ingredients")]/ul/li'):
                ingredients.append(CleanText('.')(el))
            return ingredients

        obj_cooking_time = Time(CleanText('//span[@class="cooktime"]'))
        obj_preparation_time = Time(CleanText('//span[@class="preptime"]'))

        def obj_nb_person(self):
            return [Type(CleanText('//span[@class="yield"]'), type=int)(self)]

        obj_instructions = CleanHTML('//div[@class="recette_etapes"]')
        obj_picture_url = CleanText('//section[has-class("recette_infos")]/div/img[@class="photo"]/@src')
        obj_author = CleanText('//span[@class="author"]', default=NotAvailable)
