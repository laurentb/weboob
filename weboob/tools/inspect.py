# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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


import webkit_mechanize_browser.page


class Page(webkit_mechanize_browser.page.Page):
    def load_uri(self, uri):
        self.core.location(uri)
        if self.core.page:
            data = self.core.parser.tostring(self.core.page.document)
            self.view.load_html_string(data, uri)
        else:
            webkit_mechanize_browser.page.Page.load_uri(self, uri)
