# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014  Florent Fourcot
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

from .history import BadUTF8Page
from weboob.capabilities.bill import Subscription
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Field, Format


class HomePage(BadUTF8Page):
    def is_here(self):
        if len(self.doc.xpath('//form[@id="form_connect"]')) > 0:
            return False

        return True

    @property
    def logged(self):
        return self.is_here()

    @method
    class get_list(ListElement):
        item_xpath = '//div[@class="abonne"]'

        class item(ItemElement):
            klass = Subscription

            obj_subscriber = CleanText('div[@class="idAbonne pointer"]/p[1]', symbols='-', children=False)
            obj_id = CleanText('div[@class="idAbonne pointer"]/p/span')
            obj_label = Format(u'%s - %s', Field('id'), CleanText('(.//div[@class="section-contenu"])[1]', children=False))
