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
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.deprecated.browser import Page


class ResultsPage(Page):
    """ Page which contains results as a list of recipies
    """

    def iter_recipes(self):
        for div in self.parser.select(self.document.getroot(), 'div.m_search_result'):
            tds = self.parser.select(div, 'td')
            if len(tds) == 2:
                title = NotAvailable
                thumbnail_url = NotAvailable
                short_description = NotAvailable
                imgs = self.parser.select(tds[0], 'img')
                if len(imgs) > 0:
                    thumbnail_url = unicode(imgs[0].attrib.get('src', ''))
                link = self.parser.select(tds[1], 'div.m_search_titre_recette a', 1)
                title = unicode(link.text)
                id = link.attrib.get('href', '').replace('.aspx', '').replace('/recettes/recette_', '')
                short_description = unicode(' '.join(self.parser.select(tds[
                                            1], 'div.m_search_result_part4', 1).text.strip().split('\n')))

                recipe = Recipe(id, title)
                recipe.thumbnail_url = thumbnail_url
                recipe.short_description = short_description
                recipe.instructions = NotLoaded
                recipe.author = NotLoaded
                recipe.ingredients = NotLoaded
                recipe.nb_person = NotLoaded
                recipe.cooking_time = NotLoaded
                recipe.preparation_time = NotLoaded
                yield recipe


class RecipePage(Page):
    """ Page which contains a recipe
    """

    def get_recipe(self, id):
        title = NotAvailable
        preparation_time = NotAvailable
        cooking_time = NotAvailable
        nb_person = NotAvailable
        ingredients = NotAvailable
        picture_url = NotAvailable
        instructions = NotAvailable
        comments = NotAvailable

        title = unicode(self.parser.select(self.document.getroot(), 'h1.m_title', 1).text_content().strip())
        main = self.parser.select(self.document.getroot(), 'div.m_content_recette_main', 1)
        preparation_time = int(self.parser.select(main, 'p.m_content_recette_info span.preptime', 1).text_content())
        cooking_time = int(self.parser.select(main, 'p.m_content_recette_info span.cooktime', 1).text_content())
        ing_header_line = self.parser.select(main, 'p.m_content_recette_ingredients span', 1).text_content()
        if '(pour' in ing_header_line and ')' in ing_header_line:
            nb_person = [int(ing_header_line.split('pour ')[-1].split('personnes)')[0].split()[0])]
        ingredients = self.parser.select(main, 'p.m_content_recette_ingredients', 1).text_content().strip().split('- ')
        ingredients = ingredients[1:]
        rinstructions = self.parser.select(main, 'div.m_content_recette_todo', 1).text_content().strip()
        instructions = u''
        for line in rinstructions.split('\n'):
            instructions += '%s\n' % line.strip()
        instructions = instructions.strip('\n')
        imgillu = self.parser.select(self.document.getroot(), 'a.m_content_recette_illu img')
        if len(imgillu) > 0:
            picture_url = unicode(imgillu[0].attrib.get('src', ''))

        divcoms = self.parser.select(self.document.getroot(), 'div.m_commentaire_row')
        if len(divcoms) > 0:
            comments = []
            for divcom in divcoms:
                note = self.parser.select(divcom, 'div.m_commentaire_note span', 1).text.strip()
                user = self.parser.select(divcom, 'div.m_commentaire_content span', 1).text.strip()
                content = self.parser.select(divcom, 'div.m_commentaire_content p', 1).text.strip()
                comments.append(Comment(author=user, rate=note, text=content))

        recipe = Recipe(id, title)
        recipe.preparation_time = preparation_time
        recipe.cooking_time = cooking_time
        recipe.nb_person = nb_person
        recipe.ingredients = ingredients
        recipe.instructions = instructions
        recipe.picture_url = picture_url
        recipe.comments = comments
        recipe.thumbnail_url = NotLoaded
        recipe.author = NotAvailable
        return recipe
