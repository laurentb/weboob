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


from .base import Capability, BaseObject, StringField, IntField, Field, empty

import lxml.etree as ET
import requests

import base64
import re


__all__ = ['Recipe', 'CapRecipe']


class Comment(BaseObject):
    author = StringField('Author of the comment')
    rate = StringField('Rating')
    text = StringField('Comment')

    def __unicode__(self):
        result = u''
        if self.author:
            result += u'author: %s, ' % self.author
        if self.rate:
            result += u'note: %s, ' % self.rate
        if self.text:
            result += u'comment: %s' % self.text
        return result


class Recipe(BaseObject):
    """
    Recipe object.
    """
    title =             StringField('Title of the recipe')
    author =            StringField('Author name of the recipe')
    thumbnail_url =     StringField('Direct url to recipe thumbnail')
    picture_url =       StringField('Direct url to recipe picture')
    short_description = StringField('Short description of a recipe')
    nb_person =         Field('The recipe was made for this amount of persons', list)
    preparation_time =  IntField('Preparation time of the recipe in minutes')
    cooking_time =      IntField('Cooking time of the recipe in minutes')
    ingredients =       Field('Ingredient list necessary for the recipe', list)
    instructions =      StringField('Instruction step list of the recipe')
    comments =          Field('User comments about the recipe', list)

    def __init__(self, id='', title=u'', url=None):
        super(Recipe, self).__init__(id, url)
        self.title = title

    def toKrecipesXml(self, author=None):
        """
        Export recipe to KRecipes XML string
        """
        sauthor = u''
        if not empty(self.author):
            sauthor += '%s@' % self.author

        if author is None:
            sauthor += 'Cookboob'
        else:
            sauthor += author

        header = u'<?xml version="1.0" encoding="UTF-8" ?>\n'
        initial_xml = '''\
<krecipes version='2.0-beta2' lang='fr' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xsi:noNamespaceSchemaLocation='krecipes.xsd'>
<krecipes-recipe id='1'>
</krecipes-recipe>
</krecipes>'''
        doc = ET.fromstring(initial_xml)
        recipe = doc.find('krecipes-recipe')
        desc = ET.SubElement(recipe, 'krecipes-description')
        title = ET.SubElement(desc, 'title')
        title.text = self.title
        authors = ET.SubElement(desc, 'author')
        authors.text = sauthor
        eyield = ET.SubElement(desc, 'yield')
        if not empty(self.nb_person):
            amount = ET.SubElement(eyield, 'amount')
            if len(self.nb_person) == 1:
                amount.text = '%s' % self.nb_person[0]
            else:
                mini = ET.SubElement(amount, 'min')
                mini.text = u'%s' % self.nb_person[0]
                maxi = ET.SubElement(amount, 'max')
                maxi.text = u'%s' % self.nb_person[1]
            etype = ET.SubElement(eyield, 'type')
            etype.text = 'persons'
        if not empty(self.preparation_time):
            preptime = ET.SubElement(desc, 'preparation-time')
            preptime.text = '%02d:%02d' % (self.preparation_time / 60, self.preparation_time % 60)
        if not empty(self.picture_url) and self.picture_url != '':
            data = requests.get(self.picture_url).content
            datab64 = base64.encodestring(data)[:-1]

            pictures = ET.SubElement(desc, 'pictures')
            pic = ET.SubElement(pictures, 'pic', {'format': 'JPEG', 'id': '1'})
            pic.text = ET.CDATA(datab64)

        if not empty(self.ingredients):
            ings = ET.SubElement(recipe, 'krecipes-ingredients')
            pat = re.compile('^[0-9,.]*')
            for i in self.ingredients:
                sname = u'%s' % i
                samount = ''
                sunit = ''
                first_nums = pat.match(i).group()
                if first_nums != '':
                    samount = first_nums
                    sname = i.lstrip('0123456789 ')

                ing = ET.SubElement(ings, 'ingredient')
                am = ET.SubElement(ing, 'amount')
                am.text = samount
                unit = ET.SubElement(ing, 'unit')
                unit.text = sunit
                name = ET.SubElement(ing, 'name')
                name.text = sname

        if not empty(self.instructions):
            instructions = ET.SubElement(recipe, 'krecipes-instructions')
            instructions.text = self.instructions

        if not empty(self.comments):
            ratings = ET.SubElement(recipe, 'krecipes-ratings')
            for c in self.comments:
                rating = ET.SubElement(ratings, 'rating')
                if c.author:
                    rater = ET.SubElement(rating, 'rater')
                    rater.text = c.author
                if c.text:
                    com = ET.SubElement(rating, 'comment')
                    com.text = c.text
                crits = ET.SubElement(rating, 'criterion')
                if c.rate:
                    crit = ET.SubElement(crits, 'criteria')
                    critname = ET.SubElement(crit, 'name')
                    critname.text = 'Overall'
                    critstars = ET.SubElement(crit, 'stars')
                    critstars.text = c.rate.split('/')[0]

        return header + ET.tostring(doc, encoding='UTF-8', pretty_print=True).decode('utf-8')


class CapRecipe(Capability):
    """
    Recipe providers.
    """

    def iter_recipes(self, pattern):
        """
        Search recipes and iterate on results.

        :param pattern: pattern to search
        :type pattern: str
        :rtype: iter[:class:`Recipe`]
        """
        raise NotImplementedError()

    def get_recipe(self, _id):
        """
        Get a recipe object from an ID.

        :param _id: ID of recipe
        :type _id: str
        :rtype: :class:`Recipe`
        """
        raise NotImplementedError()
