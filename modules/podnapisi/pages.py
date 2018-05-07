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
from __future__ import unicode_literals

from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.html import TableCell, AbsoluteLink, Attr
from weboob.browser.filters.standard import CleanText, Field, Type, Regexp
from weboob.capabilities.subtitle import Subtitle
from weboob.tools.compat import urljoin


class SearchPage(HTMLPage):
    """ Page which contains results as a list of movies
    """
    @pagination
    @method
    class iter_subtitles(TableElement):
        head_xpath = '//div[has-class("table-responsive")]/table/thead/tr/th'
        item_xpath = '//tr[has-class("subtitle-entry")]'

        col_cd = u'# CDs'
        col_language = u'Language'

        next_page = AbsoluteLink('//ul[has-class("pagination")]/li[has-class("next")]/a', default=None)

        class item(ItemElement):
            klass = Subtitle

            obj_name = CleanText('.//td/a[@alt="Subtitles\' page"]')
            obj_nb_cd = Type(CleanText(TableCell('cd')), type=int)
            obj_language = CleanText(TableCell('language'))
            obj_url = AbsoluteLink('.//td/div[has-class("pull-left")]/a[@alt="Download subtitles."]')
            obj_id = Regexp(Field('url'), r'/(-*\w*)/download$', r'\1')


class SubtitlePage(HTMLPage):
    @method
    class get_subtitle(ItemElement):
        klass = Subtitle

        obj_id = CleanText('//div[has-class("col-md-3")]/table[has-class("table-condensed")]/tr[1]/td')
        obj_language = Regexp(
            CleanText(
                Attr('//div[has-class("col-md-3")]/table[has-class("table-condensed")]/tr/td/a/span', 'class')
            ),
            r'-(\w*)$', r'\1'
        )
        obj_name = CleanText('//div[has-class("clearfix")]/table[has-class("table-condensed")]/tr[1]/td/a')

        def obj_url(self):
            return urljoin(self.page.browser.BASEURL,
                           CleanText(Attr('//form[has-class("download-form")]', 'action'))(self))
