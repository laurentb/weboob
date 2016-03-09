# -*- coding: utf-8 -*-

from weboob.tools.test import BackendTest
from weboob.capabilities.torrent import MagnetOnly

from random import choice


class BTDiggTest(BackendTest):
    MODULE = 'btdigg'

    def test_iter_torrents(self):
        # try something popular so we sometimes get a magnet-only torrent
        l = list(self.backend.iter_torrents('ubuntu linux'))
        self.assertTrue(len(l) == 10)
        for torrent in l:
            assert torrent.name
            assert torrent.size
            assert torrent.magnet
            assert torrent.date

            self.assertEquals(40, len(torrent.id))

    def test_get_random_torrentfile(self):
        torrent = choice(list(self.backend.iter_torrents('ubuntu linux')))
        full_torrent = self.backend.get_torrent(torrent.id)
        try:
            self.backend.get_torrent_file(torrent.id)
        except MagnetOnly as e:
            assert e.magnet.startswith("magnet:")
            assert e.magnet == full_torrent.magnet

    def test_get_special_torrent(self):
        torrent = self.backend.get_torrent("abd1d2648c97958789d62f6a6a1f5d33f4eff5be")
        assert torrent.name == u'Ubuntu Linux Toolbox - 1000+ Commands for Ubuntu and Debian Power Users'
        assert len(torrent.files) == 3
        assert torrent.size == float(7004487.68)
        dt = torrent.date
        assert dt.year == 2013
        assert dt.month == 12
