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
from weboob.browser.filters.standard import Regexp, CleanText, Format, Env, Type
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """
    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//div[has-class("recette_classique")]'

        def next_page(self):
            return CleanText('//a[@id="ctl00_cphMainContent_m_ctrlSearchEngine_m_ctrlSearchListDisplay_m_ctrlSearchPagination_m_linkNextPage"]/@href',
                             default=None)(self)

        class item(ItemElement):
            klass = Recipe
            obj_id = Regexp(CleanText('./div/div[@class="m_titre_resultat"]/a/@href'),
                            '/recettes/recette_(.*).aspx')
            obj_title = CleanText('./div/div[@class="m_titre_resultat"]/a')
            obj_short_description = Format('%s. %s',
                                           CleanText('./div/div[@class="m_detail_recette"]'),
                                           CleanText('./div/div[@class="m_texte_resultat"]'))


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """
    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('id')
        obj_title = CleanText('//h1[@class="m_title"]')
        obj_preparation_time = Type(CleanText('//span[@class="preptime"]'), type=int)
        obj_cooking_time = Type(CleanText('//span[@class="cooktime"]'), type=int)

        def obj_nb_person(self):
            nb_pers = Regexp(CleanText('//p[@class="m_content_recette_ingredients"]/span[1]'),
                             '.*\(pour (\d+) personnes\)', default=0)(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            ingredients = CleanText('//p[@class="m_content_recette_ingredients"]', default='')(self).split('-')
            if len(ingredients) > 1:
                return ingredients[1:]

        obj_instructions = CleanHTML('//div[@class="m_content_recette_todo"]')
        obj_thumbnail_url = CleanText('//a[@class="m_content_recette_illu"]/img/@src', default=NotAvailable)
        obj_picture_url = CleanText('//a[@class="m_content_recette_illu"]/img/@src', default=NotAvailable)

    @method
    class get_comments(ListElement):
        item_xpath = '//div[@class="m_commentaire_row"]'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Comment

            obj_author = CleanText('./div[@class="m_commentaire_content"]/span[1]')
            obj_rate = CleanText('./div[@class="m_commentaire_note"]/span')
            obj_text = CleanText('./div[@class="m_commentaire_content"]/p[1]')
            obj_id = CleanText('./div[@class="m_commentaire_content"]/span[1]')
