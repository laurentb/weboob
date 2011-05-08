# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.tools.browser import BaseBrowser

from .pages import PlayerPage


__all__ = ['OuiFMBrowser']


class OuiFMBrowser(BaseBrowser):
    DOMAIN = u'www.ouifm.fr'
    PAGES = {r'.*ouifm.fr/player/decode_json.*.php': PlayerPage,
            }

    def get_current(self, radio):
        if radio == 'general':
            _radio = ''
        else:
            _radio = '_%s' % radio
        self.location('/player/decode_json%s.php' % _radio)
        assert self.is_on_page(PlayerPage)

        return self.page.get_current()
