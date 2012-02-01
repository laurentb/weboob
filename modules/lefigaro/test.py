# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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
from weboob.tools.misc import html2text


__all__ = ['LeFigaroTest']


class LeFigaroTest(BackendTest):
    BACKEND = 'lefigaro'

    def test_new_messages(self):
        for message in self.backend.iter_unread_messages():
            pass

    def test_content(self):
        urls = ['http://www.lefigaro.fr/international/2011/10/24/01003-20111024ARTFIG00704-les-islamo-conservateurs-maitres-du-jeu-tunisien.php',
                'http://www.lefigaro.fr/international/2012/01/29/01003-20120129ARTFIG00191-floride-la-primaire-suspendue-a-l-humeur-des-hispaniques.php']

        for url in urls:
            thread = self.backend.get_thread(url)
            assert len(thread.root.content)
            assert '<script' not in thread.root.content
            assert 'object' not in thread.root.content
            assert 'BFM' not in thread.root.content

            assert 'AUSSI' not in thread.root.content

            # no funny tags means html2text does not crash
            assert len(html2text(thread.root.content))
