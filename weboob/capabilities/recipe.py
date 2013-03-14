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


from .base import IBaseCap, CapBaseObject, StringField, IntField, Field


__all__ = ['Recipe', 'ICapRecipe']


class Recipe(CapBaseObject):
    """
    Recipe object.
    """
    title =             StringField('Title of the recipe')
    thumbnail_url =     StringField('Direct url to recipe thumbnail')
    picture_url =       StringField('Direct url to recipe picture')
    short_description = StringField('Short description of a recipe')
    nb_person =         IntField('The recipe was made for this amount of persons')
    preparation_time =  IntField('Preparation time of the recipe in minutes')
    cooking_time =      IntField('Cooking time of the recipe in minutes')
    ingredients =       Field('Ingredient list necessary for the recipe',list)
    instructions =      StringField('Instruction step list of the recipe')
    comments =          Field('User comments about the recipe',list)

    def __init__(self, id, title):
        CapBaseObject.__init__(self, id)
        self.title = title


class ICapRecipe(IBaseCap):
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
