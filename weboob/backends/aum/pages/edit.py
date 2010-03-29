# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backends.aum.pages.base import PageBase

class EditPhotoPage(PageBase):
    def add_photo(self, name, f):
        self.browser.select_form(name="form")
        self.browser.find_control('uploaded').add_file(f, 'image/jpeg', name)
        self.browser.submit()
        self.browser.openurl('http://www.adopteunmec.com/home.php')

class EditPhotoCbPage(PageBase):
    # Do nothing
    pass

class EditAnnouncePage(PageBase):
    def set_nickname(self, nickname):
        self.browser.select_form(name="form")
        self.browser['pseudo'] = nickname
        self.browser.submit()

    def set_announce(self, **kwargs):
        self.browser.select_form(name="form")
        self.browser.set_field(kwargs, 'title')
        self.browser.set_field(kwargs, 'description', field='about1')
        self.browser.set_field(kwargs, 'lookingfor', field='about2')

        self.browser.submit()

class EditDescriptionPage(PageBase):
    SHAPES = ['--', 'svelte', 'sportive', u'équilibrée', 'pulpeuse', u'généreuse', 'normale']
    HAIR_COLORS = ['--', 'blancs', 'gris', 'noirs', 'bruns', 'chatains', 'roux', 'blonds', 'platines', u'colorés']
    HAIR_SIZES = ['--', u'rasés', 'courts', 'mi-longs', 'longs']
    EYES = ['--', 'noirs', 'marrons', 'noisettes', 'bleus', 'verts', 'gris']
    ORIGINS = ['--', u'européennes', 'afro', 'maghrebines', 'asiatiques', u'métisses', 'eurasiennes', 'latines']
    STYLES = ['--', 'fashion', 'chic', 'sport', u'décontracté', 'rock', u'bohème', 'masculin', 'dark', 'excentrique', 'electro', 'skate']
    FOODS = ['--', 'mange de tout', 'piscovore', u'végétarien', u'végétalien', 'bio']
    DRINKS = ['--', 'jamais', 'de temps en temps', 'souvent', 'pilier de bar']
    SMOKES = ['--', u'ne tolère pas la fumée', u'tolère la fumée', 'fume de temps en temps', 'fume souvent']

    def set_description(self, **kwargs):
        self.browser.select_form(name='form')

        self.browser.set_field(kwargs, 'height', field='size', is_list=True)
        self.browser.set_field(kwargs, 'weight', is_list=True)
        self.browser.set_field(kwargs, 'shape', is_list=self.SHAPES)
        self.browser.set_field(kwargs, 'hair_color', is_list=self.HAIR_COLORS)
        self.browser.set_field(kwargs, 'hair_size', is_list=self.HAIR_SIZES)
        self.browser.set_field(kwargs, 'eyes', is_list=self.EYES)
        self.browser.set_field(kwargs, 'origins', is_list=self.ORIGINS)
        self.browser.set_field(kwargs, 'style', is_list=self.STYLES)
        self.browser.set_field(kwargs, 'food', is_list=self.FOODS)
        self.browser.set_field(kwargs, 'drink', is_list=self.DRINKS)
        self.browser.set_field(kwargs, 'smoke', is_list=self.SMOKES)

        self.browser.submit()

class EditSexPage(PageBase):
    pass

class EditPersonalityPage(PageBase):
    pass
