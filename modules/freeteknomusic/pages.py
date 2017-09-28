# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp
from weboob.browser.filters.html import AbsoluteLink
from weboob.capabilities.collection import Collection
from weboob.capabilities.audio import BaseAudio
from weboob.tools.compat import urlparse


class FolderPage(HTMLPage):
    def get_split_path(self):
        ret = urlparse(self.url).path.split('/')[1:]
        if not ret[0]:
            ret = ret[1:]
        return ret

    @method
    class iter_dirs(ListElement):
        item_xpath = '//table/tr'

        class item(ItemElement):
            def condition(self):
                alt = self.el.xpath('./td/img/@alt')
                if not alt or alt[0] != '[DIR]':
                    return False
                if self.obj_title(self) == 'Parent Directory':
                    return False
                return True

            klass = Collection

            obj_title = CleanText('./td/a')
            obj_url = AbsoluteLink('./td/a')

            def obj_split_path(self):
                return self.page.get_split_path() + [self.obj_title(self)]

            def obj_id(self):
                return 'album.%s' % '/'.join(self.obj_split_path())

    @method
    class iter_files(ListElement):
        item_xpath = '//table/tr'

        class item(ItemElement):
            def condition(self):
                return (self.el.xpath('./td/img/@alt') or 'x')[0] == '[SND]'

            klass = BaseAudio

            filename = CleanText('./td/a')

            obj_title = Regexp(filename, r'(.*)\.[^.]+$')
            obj_ext = Regexp(filename, r'\.([^.]+)$')
            obj_format = obj_ext
            obj_url = AbsoluteLink('./td/a')

            def obj_id(self):
                return 'audio.%s' % '/'.join(self.page.get_split_path() + [self.filename(self)])
