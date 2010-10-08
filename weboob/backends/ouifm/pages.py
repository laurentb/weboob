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


from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select


__all__ = ['PlayerPage']


class PlayerPage(BasePage):
    def get_current(self, radio):
        if radio == 'general':
            _radio = ''
        else:
            _radio = '_%s' % radio
        title = select(self.document.getroot(), 'div#titre%s' % _radio, 1).text.strip()
        artist = select(self.document.getroot(), 'div#artiste%s' % _radio, 1).text.strip()
        return artist, title
