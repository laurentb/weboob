# * -*- coding: utf-8 -*-

# Copyright(C) 2011  Johann Broudin
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


__all__ = ['XMLinfos']


class XMLinfos(BasePage):
    def get_current(self):
        try:
            for channel in select(self.document.getroot(), 'channel'):
                title = channel.find('item/song_title').text
                artist = channel.find('item/artist_name').text
        except AttributeError:
            title = "Not defined"
            artist = "Not defined"

        return unicode(artist).strip(), unicode(title).strip()
