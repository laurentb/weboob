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

import re

from itertools import chain

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import TableElement, ListElement, ItemElement, method
from weboob.browser.filters.html import TableCell, AbsoluteLink, Attr
from weboob.browser.filters.standard import CleanText, Regexp, Field, Map, CleanDecimal
from weboob.capabilities.base import NotLoaded, empty
from weboob.capabilities.rpg import (
    Character, Skill, SkillType, SkillTarget, SkillCategory, CharacterClass, CollectableItem,
)


SKILL_TARGETS = {
    'Self': SkillTarget.SELF,
    'Selected Target': SkillTarget.FOE,
    'Field': SkillTarget.FIELD,
    'All Adjacent Pokémon': SkillTarget.SELF_AND_FOE,
}


SKILL_CATEGORY = {
    'physical': SkillCategory.PHYSICAL,
    'special': SkillCategory.MAGICAL,
    'other': SkillCategory.STATUS,
}


def get_id_from_name(name):
    return name.lower().replace(' ', '_')


class iter_character_moves(ListElement):
    ignore_duplicate = True

    class item(ItemElement):
        klass = Skill

        obj_type = SkillType.ACTIVE

        obj_name = CleanText('./td[a[contains(@href, "attackdex")]]')
        obj_url = AbsoluteLink('./td/a[contains(@href, "attackdex")]')
        obj_description = CleanText('./following::tr[1]/td')
        obj_category = Map(
            Regexp(Attr('.//img[contains(@src, "type") and contains(@src, "png")]', 'src'), r'/(\w+)\.png'),
            SKILL_CATEGORY, SkillCategory.UNKNOWN
        )

        def obj_id(self):
            return get_id_from_name(Field('name')(self))

        def obj_character_classes(self):
            types = []
            for _type in self.xpath('.//img[contains(@src, "type")]/@src'):
                m = re.search(r'/(\w+)\.gif', _type)
                if m:
                    types.append(m.group(1))
            return types


class PkmnListPage(HTMLPage):
    @method
    class iter_pokemons(ListElement):
        item_xpath = '//select[not(option[contains(text(), "Pokédex") or contains(@value, "breed")])]/option[contains(@value, "pokedex")]'

        class item(ItemElement):
            klass = Character

            obj_id = Regexp(CleanText('.'), r'(\d+) \w+', default=None)
            obj_name = Regexp(CleanText('.'), r'\d+ (\w+)', default=None)
            obj_url = Attr('.', 'value')

            def validate(self, obj):
                return not(empty(obj.id) or empty(obj.name))


class PkmnDetailsPage(HTMLPage):
    @method
    class iter_abilities(ListElement):
        item_xpath = '//table//td[@class="fooinfo"]/a[contains(@href, "abilitydex")]'

        class item(ItemElement):
            klass = Skill

            obj_type = SkillType.PASSIVE

            obj_name = CleanText('.')
            obj_url = AbsoluteLink('.')
            obj_description = Regexp(CleanText('./following::text()'), r': (.*?)\.')

            def obj_id(self):
                return get_id_from_name(Field('name')(self))

    @method
    class iter_moves_1(iter_character_moves):
        item_xpath = '//table[.//th[contains(text(), "Attack")]][position()>=1 and position()<4]//tr[.//img]'

        def obj_statistics(self):
            return {
                'base_power': CleanDecimal('./td[5]', default=NotLoaded)(self),
                'accuracy': CleanDecimal('./td[6]')(self),
                'power_point': CleanDecimal('./td[7]')(self),
                'effect_rate': CleanDecimal('./td[8]', default=NotLoaded)(self),
            }

    @method
    class iter_moves_2(iter_character_moves):
        item_xpath = '//table[.//th[contains(text(), "Attack")]][position()>=4]//tr[.//img]'

        def obj_statistics(self):
            return {
                'base_power': CleanDecimal('./td[4]', default=NotLoaded)(self),
                'accuracy': CleanDecimal('./td[5]')(self),
                'power_point': CleanDecimal('./td[6]')(self),
                'effect_rate': CleanDecimal('./td[7]', default=NotLoaded)(self),
            }

    def iter_moves(self):
        for move in chain(self.iter_moves_1(), self.iter_moves_2()):
            yield move

    @method
    class fill_pkmn(ItemElement):
        obj_description = CleanText('//table[.//td[contains(text(), "Text")]]//td[@class="fooinfo"]')

        def obj_character_classes(self):
            types = []
            for _type in self.xpath('//table[.//tr//td[contains(text(), "Type")] and @class="dextable"]//img/@src'):
                m = re.search(r'/(\w+)\.gif', _type)
                if m:
                    types.append(m.group(1))

            return types

        def obj_skills(self):
            return [skill.id for skill in chain(self.page.iter_abilities(), self.page.iter_moves())]

        def obj_next_forms(self):
            next_forms = []
            passed_current_pkmn = False

            # an evolution is a picture which is after the one of the current pokemon
            for pkmn in self.xpath('//img[contains(@src, "pokemon")]/@src')[1:]:
                m = re.search(r'/(\d+).png', pkmn)
                if m:
                    pkmn_id = m.group(1)
                    if pkmn_id == self.obj.id:
                        passed_current_pkmn = True
                        continue

                    if passed_current_pkmn:
                        next_forms.append(pkmn_id)

            return next_forms

        def obj_base_stats(self):
            xpath = '//table[.//h2[contains(text(), "Stats")]]//tr[7]'
            return {
                'health_point': CleanDecimal(Regexp(CleanText('%s/td[2]' % xpath), r'\d+ - (\d+)'))(self),
                'attack': CleanDecimal(Regexp(CleanText('%s/td[3]' % xpath), r'\d+ - (\d+)'))(self),
                'defense': CleanDecimal(Regexp(CleanText('%s/td[4]' % xpath), r'\d+ - (\d+)'))(self),
                'special_attack': CleanDecimal(Regexp(CleanText('%s/td[5]' % xpath), r'\d+ - (\d+)'))(self),
                'special_defense': CleanDecimal(Regexp(CleanText('%s/td[6]' % xpath), r'\d+ - (\d+)'))(self),
                'speed': CleanDecimal(Regexp(CleanText('%s/td[7]' % xpath), r'\d+ - (\d+)'))(self),
            }


class Gen8AttackDexPage(HTMLPage):
    @method
    class iter_moves(ListElement):
        item_xpath = '//option[@value]'

        ignore_duplicate = True

        class item(ItemElement):
            klass = Skill

            obj_type = SkillType.ACTIVE

            obj_name = CleanText('.')
            obj_url = Attr('.', 'value')

            def obj_id(self):
                return get_id_from_name(Field('name')(self))

    @method
    class fill_skill(ItemElement):
        base_xpath = '//a[contains(@name, "details")]/following::table[1]//tr[not(ancestor::tr)][position()>1]'
        #def parse(self, el):
        #    self.el = el.xpath('//a[contains(@name, "details")]/following::table[1]//tr[not(ancestor::tr)][position()>1]')

        def obj_character_classes(self):
            types = []
            for _type in self.xpath('%s[1]//img[not(contains(@src, "game"))]/@src' % self.base_xpath):
                m = re.search(r'/(\w+)\.gif', _type)
                if m:
                    types.append(m.group(1))
            return types

        def obj_target(self):
            return Map(
                CleanText('%s[last()]/td[3]' % self.base_xpath),
                SKILL_TARGETS, SkillTarget.UNKNOWN
            )(self)

        def obj_category(self):
            return Map(
                Regexp(
                    CleanText('%s[1]/td[3]//img/@src' % self.base_xpath),
                    r'/(\w+)\.png'
                ), SKILL_CATEGORY, SkillCategory.UNKNOWN
            )(self)

        def obj_description(self):
            return '\n'.join(CleanText('./td[1]')(txt) for txt in self.xpath(self.base_xpath)[4:8:2])

        def obj_statistics(self):
            return {
                'power_point': CleanDecimal('%s[3]/td[1]' % self.base_xpath)(self),
                'base_power': CleanDecimal('%s[3]/td[2]' % self.base_xpath)(self),
                'accuracy': CleanDecimal('%s[3]/td[3]' % self.base_xpath)(self),
                'effect_rate': CleanDecimal('%s[7]/td[2]' % self.base_xpath, default=NotLoaded)(self),
                'base_critical_hit_rate': CleanDecimal('%s[last()]/td[1]' % self.base_xpath, default=NotLoaded)(self),
                'speed_priority': CleanDecimal('%s[last()]/td[2]' % self.base_xpath, default=NotLoaded)(self),
            }



class AbilitiesPage(HTMLPage):
    @method
    class iter_abilities(ListElement):
        item_xpath = '//option[contains(@value, "abilitydex")]'

        class item(ItemElement):
            klass = Skill

            obj_type = SkillType.PASSIVE

            obj_name = CleanText('.')
            obj_url = Attr('.', 'value')

            def obj_id(self):
                return get_id_from_name(Field('name')(self))

    @method
    class fill_skill(ItemElement):
        obj_description = CleanText('//a[contains(@name, "details")]/following::table[1]//tr[position()>2]')


class XYTypePage(HTMLPage):
    @method
    class iter_types(ListElement):
        item_xpath = '//tr/td/img[contains(@src, "2.gif")]'

        ignore_duplicate = True

        class item(ItemElement):
            klass = CharacterClass

            def obj_name(self):
                return Regexp(Attr('.', 'src'), r'/(\w+)2\.gif')(self).capitalize()

            def obj_id(self):
                return get_id_from_name(Field('name')(self))

    def fill_type(self, pkmn_type):
        attack_lst = self.doc.xpath('//tr/td/img[contains(@src, "2.gif")]/@src')
        row = self.doc.xpath('//tr[td/a[contains(@href, "%s")]][1]/td[position()>1]' % pkmn_type.id)

        weaknesses = []
        resistances = []
        no_effect = []

        for attack, cell in zip(attack_lst, row):
            if cell.xpath('./img'):
                damage = CleanText('./img/@alt')(cell)
                type_id = get_id_from_name(re.search(r'/(\w+)2.gif', attack).group(1))
                if damage == '*2 Damage':
                    weaknesses.append(type_id)
                elif damage == '*0.5 Damage':
                    resistances.append(type_id)
                else:   #damage == '*0 Damage'
                    no_effect.append(type_id)

        pkmn_type.description = 'A Pokémon with the type %s undergoes\nWeakness: %s\nResistance: %s\nNo Effect: %s' % (
            pkmn_type.name, ', '.join(weaknesses), ', '.join(resistances), ', '.join(no_effect)
        )

        return pkmn_type


CATEGORIES_TO_USE = (
    'PokéBalls', 'Evolutionary Items', 'Miscellaneous Items', 'Recovery Items',
    'Battle Effect Items', 'Fossils', 'Berries', 'Vitamins', 'Ingredients',
    'Dynamax Crystals', 'Key Items',
)


CATEGORIES_TO_CARRY = (
    'Berries', 'Hold Items',
)


class ItemsPage(HTMLPage):
    @method
    class iter_collectable_items(TableElement):
        head_xpath = '//table[1]//tr[1]/td'
        item_xpath = '//table//tr[position()>1]'

        col_name = 'Name'
        col_effect = 'Effect'

        ignore_duplicate = True

        class item(ItemElement):
            klass = CollectableItem

            obj_name = CleanText(TableCell('name'))
            obj_description = CleanText(TableCell('effect'))
            obj_category = CleanText('.//preceding::font[1]//u')

            def obj_id(self):
                return get_id_from_name(Field('name')(self))

            def obj_to_use(self):
                return Field('category')(self) in CATEGORIES_TO_USE

            def obj_to_carry(self):
                return Field('category')(self) in CATEGORIES_TO_CARRY
