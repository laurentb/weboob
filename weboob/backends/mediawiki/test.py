# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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


from weboob.tools.test import BackendTest
from datetime import datetime

class MediawikiTest(BackendTest):
    BACKEND = 'mediawiki'

    def test_get_content(self):
        self.backend.get_content(u"Utilisateur:Clemux/Test")

    def test_iter_revisions(self):
        for rev in self.backend.iter_revisions(u"Utilisateur:Clemux/Test"):
            pass

    def test_push_content(self):
        content = self.backend.get_content(u"Utilisateur:Clemux/Test")
        content.content = "test "+str(datetime.now())
        self.backend.push_content(content, message="test weboob", minor=True)

    def test_content_preview(self):
        content = self.backend.get_content(u"Utilisateur:Clemux/Test")
        self.backend.get_content_preview(content)
