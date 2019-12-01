# -*- coding: utf-8 -*-

# Copyright(C) 2019-2020 Célande Adrien
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.browser import PagesBrowser, URL
from weboob.capabilities.base import find_object
from weboob.capabilities.rpg import SkillType, SkillNotFound, CharacterNotFound, CharacterClassNotFound

from .pages import (
    PkmnListPage, PkmnDetailsPage, Gen8AttackDexPage,
    AbilitiesPage, XYTypePage, ItemsPage,
)


class SerebiiBrowser(PagesBrowser):
    BASEURL = 'https://www.serebii.net'

    # pokemon
    pkmn_list = URL(r'/pokedex-swsh/$', PkmnListPage)
    pkmn_details = URL(r'/pokedex-swsh/(?P<pkmn_id>.*)/', PkmnDetailsPage)

    # skills
    gen8_attack_dex = URL(r'/attackdex-swsh/', Gen8AttackDexPage)
    abilities = URL(r'/abilitydex/', AbilitiesPage)

    # clases
    types = URL(r'/games/typexy.shtml$', XYTypePage)

    # items
    items = URL(r'/swordshield/items.shtml$', ItemsPage)

    def iter_characters(self):
        self.pkmn_list.go()
        return self.page.iter_pokemons()

    def get_character(self, character_id):
        pokemon = find_object(self.iter_characters(), id=character_id, error=CharacterNotFound)
        self.location(pokemon.url)
        return self.page.fill_pkmn(obj=pokemon)

    def iter_skills(self, skill_type=None):
        # passive first beacause there is less
        if skill_type is None or int(skill_type) == SkillType.PASSIVE:
            self.abilities.go()
            for skill in self.page.iter_abilities():
                yield skill

        if skill_type is None or int(skill_type) == SkillType.ACTIVE:
            self.gen8_attack_dex.go()
            for skill in self.page.iter_moves():
                yield skill

    def get_skill(self, skill_id):
        skill = find_object(self.iter_skills(), id=skill_id, error=SkillNotFound)
        self.location(skill.url)
        return self.page.fill_skill(obj=skill)

    def iter_skill_set(self, character_id, skill_type=None):
        pokemon = find_object(self.iter_characters(), id=character_id, error=CharacterNotFound)
        self.location(pokemon.url)

        if skill_type is None or int(skill_type) == SkillType.PASSIVE:
            for ability in self.page.iter_abilities():
                yield ability

        if skill_type is None or int(skill_type) == SkillType.ACTIVE:
            for move in self.page.iter_moves():
                yield move

    def iter_character_classes(self):
        self.types.go()
        return self.page.iter_types()

    def get_character_class(self, class_id):
        pkmn_type = find_object(self.iter_classes(), id=class_id, error=CharacterClassNotFound)
        return self.page.fill_type(pkmn_type)

    def iter_collectable_items(self):
        self.items.go()
        return self.page.iter_collectable_items()
