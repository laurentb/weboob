# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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


from weboob.tools.test import BackendTest
from datetime import datetime


class MediawikiTest(BackendTest):
    MODULE = 'mediawiki'

    def test_get_content(self):
        self.backend.get_content(u"Utilisateur:Clemux/Test")

    def test_iter_revisions(self):
        for rev in self.backend.iter_revisions(u"Utilisateur:Clemux/Test"):
            pass

    def test_push_content(self):
        content = self.backend.get_content(u"Utilisateur:Clemux/Test")
        content.content = "test "+str(datetime.now())
        self.backend.push_content(content, message="test weboob", minor=True)
        new_content = self.backend.get_content(u"Utilisateur:Clemux/Test")
        assert content.content == new_content.content

    def test_content_preview(self):
        content = self.backend.get_content(u"Utilisateur:Clemux/Test")
        self.backend.get_content_preview(content)
