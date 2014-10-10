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
        for div in self.parser.select(self.document.getroot(), 'div.recette_description > div.data'):
            links = self.parser.select(div, 'div.info > p.title > a.fn')
            if len(links) > 0:
                link = links[0]
                title = unicode(link.text)
                # id = unicode(link.attrib.get('href','').strip('/').replace('.htm','htm'))
                id = unicode(self.parser.select(div, 'div.carnet-add a', 1).attrib.get('href', '').split('=')[-1])
                thumbnail_url = NotAvailable
                short_description = NotAvailable

                imgs = self.parser.select(div, 'img.recipe-image')
                if len(imgs) > 0:
                    thumbnail_url = unicode(imgs[0].attrib.get('src', ''))
                short_description = unicode(' '.join(self.parser.select(
                    div, 'div.infos_column', 1).text_content().split()).strip())
                imgs_cost = self.parser.select(div, 'div.infos_column img')
                cost_tot = len(imgs_cost)
                cost_on = 0
                for img in imgs_cost:
                    if img.attrib.get('src', '').endswith('euro_on.png'):
                        cost_on += 1
                short_description += u' %s/%s' % (cost_on, cost_tot)

                recipe = Recipe(id, title)
                recipe.thumbnail_url = thumbnail_url
                recipe.short_description = short_description
                recipe.instructions = NotLoaded
                recipe.ingredients = NotLoaded
                recipe.nb_person = NotLoaded
                recipe.cooking_time = NotLoaded
                recipe.preparation_time = NotLoaded
                recipe.author = NotLoaded
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
        author = NotAvailable
        comments = NotAvailable

        title = unicode(self.parser.select(self.document.getroot(), 'head > title', 1).text.split(' - ')[1])
        main = self.parser.select(self.document.getroot(), 'div.recette_description', 1)

        rec_infos = self.parser.select(self.document.getroot(), 'div.recette_infos div.infos_column strong')
        for info_title in rec_infos:
            if u'Temps de préparation' in unicode(info_title.text):
                if info_title.tail.strip() != '':
                    preparation_time = int(info_title.tail.split()[0])
                    if 'h' in info_title.tail:
                        preparation_time = 60*preparation_time
            if 'Temps de cuisson' in info_title.text:
                if info_title.tail.strip() != '':
                    cooking_time = int(info_title.tail.split()[0])
                    if 'h' in info_title.tail:
                        cooking_time = 60*cooking_time
            if 'Nombre de personnes' in info_title.text:
                if info_title.tail.strip() != '':
                    nb_person = [int(info_title.tail)]

        ingredients = []
        p_ing = self.parser.select(main, 'div.data.top.left > div.content p')
        for ing in p_ing:
            ingtxt = unicode(ing.text_content().strip())
            if ingtxt != '':
                ingredients.append(ingtxt)

        lines_instr = self.parser.select(main, 'div.data.top.right div.content li')
        if len(lines_instr) > 0:
            instructions = u''
            for line in lines_instr:
                inst = ' '.join(line.text_content().strip().split())
                instructions += '%s\n' % inst
            instructions = instructions.strip('\n')

        imgillu = self.parser.select(self.document.getroot(), 'div.resume_recette_illustree img.photo')
        if len(imgillu) > 0:
            picture_url = unicode(imgillu[0].attrib.get('src', ''))

        divcoms = self.parser.select(self.document.getroot(), 'div.comment-outer')
        if len(divcoms) > 0:
            comments = []
            for divcom in divcoms:
                comtxt = unicode(' '.join(divcom.text_content().strip().split()))
                if u'| Répondre' in comtxt:
                    comtxt = comtxt.strip('0123456789').replace(u' | Répondre', '')
                    author = None
                    if 'par ' in comtxt:
                        author = comtxt.split('par ')[-1].split('|')[0]
                        comtxt = comtxt.replace('par %s' % author, '')
                comments.append(Comment(text=comtxt, author=author))

        links_author = self.parser.select(self.document.getroot(), 'p.auteur a.couleur_membre')
        if len(links_author) > 0:
            author = unicode(links_author[0].text.strip())

        recipe = Recipe(id, title)
        recipe.preparation_time = preparation_time
        recipe.cooking_time = cooking_time
        recipe.nb_person = nb_person
        recipe.ingredients = ingredients
        recipe.instructions = instructions
        recipe.picture_url = picture_url
        recipe.comments = comments
        recipe.author = author
        recipe.thumbnail_url = NotLoaded
        return recipe
