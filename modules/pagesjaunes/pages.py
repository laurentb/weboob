# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from datetime import time
import re

from dateutil import rrule
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.standard import CleanText, Regexp
from weboob.browser.filters.html import AbsoluteLink, HasElement
from weboob.browser.pages import HTMLPage
from weboob.capabilities.base import NotLoaded, NotAvailable
from weboob.capabilities.contact import Place, OpeningRule


class ResultsPage(HTMLPage):
    @method
    class iter_contacts(ListElement):
        item_xpath = '//section[@id="listResults"]/article'

        class item(ItemElement):
            klass = Place

            obj_name = CleanText('.//a[has-class("denomination-links")]')
            obj_address = CleanText('.//a[has-class("adresse")]')
            obj_phone = Regexp(
                CleanText(
                    './/div[has-class("tel-zone")][span[contains(text(),"Tél")]]//strong[@class="num"]',
                    replace=[(' ', '')]), r'^0(\d{9})$', r'+33\1')
            obj_url = AbsoluteLink('.//a[has-class("denomination-links")]')
            obj_opening = HasElement('.//span[text()="Horaires"]', NotLoaded, NotAvailable)


class PlacePage(HTMLPage):
    @method
    class iter_hours(ListElement):
        item_xpath = '//ul[@class="liste-horaires-principaux"]/li[@class="horaire-ouvert"]'

        class item(ItemElement):
            klass = OpeningRule

            def obj_dates(self):
                wday = CleanText('./span')(self)
                wday = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'].index(wday)
                assert wday >= 0
                return rrule.rrule(rrule.DAILY, byweekday=wday)

            def obj_times(self):
                times = []
                for sub in self.el.xpath('.//li[@itemprop]'):
                    t = CleanText('./@content')(sub)
                    m = re.match(r'\w{2} (\d{2}):(\d{2})-(\d{2}):(\d{2})$', t)
                    m = [int(x) for x in m.groups()]
                    times.append((time(m[0], m[1]), time(m[2], m[3])))
                return times

            obj_is_open = True
