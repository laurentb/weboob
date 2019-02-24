# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from contextlib import contextmanager

from weboob.capabilities.image import BaseImage
from weboob.tools.test import BackendTest


@contextmanager
def using_url(backend, url):
    old = backend.browser.BASEURL
    try:
        backend.browser.BASEURL = url
        yield
    finally:
        backend.browser.BASEURL = old


class RedditTest(BackendTest):
    MODULE = 'reddit'

    def test_colls(self):
        colls = list(self.backend.iter_resources((BaseImage,), []))
        self.assertTrue(all(len(c.split_path) == 1 for c in colls))
        self.assertSetEqual({'hot', 'top', 'new', 'controversial', 'rising'},
                            set(c.split_path[0] for c in colls))

    def test_images(self):
        with using_url(self.backend, 'https://www.reddit.com/r/BotanicalPorn/'):
            n = -1
            for n, img in zip(range(10), self.backend.iter_resources((BaseImage,), ['hot'])):
                self.assertTrue(img.id)
                self.assertTrue(img.title)
                self.assertTrue(img.url)
                self.assertTrue(img.thumbnail.url)
                self.assertTrue(img.date)
                self.assertTrue(img.author)

            self.assertEqual(n, 9)

            new = self.backend.get_image(img.id)
            self.assertEqual(new.id, img.id)
            self.assertEqual(new.date, img.date)
            self.assertEqual(new.title, img.title)
            self.assertEqual(new.url, img.url)
            self.assertEqual(new.thumbnail.url, img.thumbnail.url)
            self.assertEqual(new.author, img.author)

    def test_search(self):
        with using_url(self.backend, 'https://www.reddit.com/r/BotanicalPorn/'):
            n = -1
            for n, img in zip(range(10), self.backend.search_image('lily')):
                self.assertTrue(img.id)
                self.assertTrue(img.title)
                self.assertTrue(img.url)
                self.assertTrue(img.thumbnail.url)
                self.assertTrue(img.date)
                self.assertTrue(img.author)

            self.assertEqual(n, 9)

    def test_thread(self):
        expanded = False

        for i, thr in zip(range(10), self.backend.iter_threads()):
            self.assertTrue(thr.title)
            self.assertTrue(thr.date)

            if not expanded:
                new = self.backend.get_thread(thr.id)
                self.assertEqual(thr.id, new.id)
                self.assertEqual(thr.title, new.title)

                j = -1

                for j, msg in enumerate(new.iter_all_messages()):
                    self.assertIs(msg.thread, new)
                    self.assertTrue(msg.title)
                    self.assertTrue(msg.sender)
                    self.assertTrue(msg.id)
                    if msg is new.root:
                        self.assertIsNone(msg.parent)
                    else:
                        self.assertTrue(msg.content)
                        self.assertTrue(msg.parent)
                        self.assertIn(msg, msg.parent.children)

                if j > 10:
                    expanded = True

        self.assertEqual(i, 9)

