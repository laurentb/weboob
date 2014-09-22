# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lord
#
# This module is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.


from weboob.tools.test import BackendTest
from weboob.capabilities.video import BaseVideo


class CappedTest(BackendTest):
    MODULE = 'cappedtv'

    def test_search(self):
        l = list(self.backend.search_videos('kewlers'))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
        self.backend.browser.openurl(v.url)

        l = list(self.backend.search_videos('weboob'))
        self.assertTrue(len(l) == 0)

    def test_latest(self):
        l = list(self.backend.iter_resources([BaseVideo], [u'latest']))
        self.assertTrue(len(l) > 0)
        v = l[0]
        self.backend.fillobj(v, ('url',))
        self.assertTrue(v.url and v.url.startswith('http://'), 'URL for video "%s" not found: %s' % (v.id, v.url))
