# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.tools.browser import BaseBrowser

from .pages import PlayerPage


__all__ = ['OuiFMBrowser']


class OuiFMBrowser(BaseBrowser):
    DOMAIN = u'www.ouifm.fr'
    PAGES = {r'.*ouifm.fr/scripts_player/decode_json.php': PlayerPage,
            }

    def get_current(self, radio):
        self.location('/scripts_player/decode_json.php')
        assert self.is_on_page(PlayerPage)

        return self.page.get_current(radio)
