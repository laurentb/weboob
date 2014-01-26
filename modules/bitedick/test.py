# -*- coding: utf-8 -*-

from weboob.tools.test import BackendTest
from weboob.capabilities.torrent import MagnetOnly

from random import choice

__all__ = ['BTDiggTest']

class BTDiggTest(BackendTest):
    BACKEND = 'btdigg'

    def test_iter_torrents(self):
        # try something popular so we sometimes get a magnet-only torrent
        l = list(self.backend.iter_torrents('ubuntu linux'))
        self.assertTrue(len(l) == 10)
        for torrent in l:
            assert torrent.name
            assert torrent.url
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
        torrent = self.backend.get_torrent("c2e018a16bf28520687e400580be08934d00373a")
        assert torrent.name == u'Ubuntu Linux Toolbox - 1000+ Commands for Ubuntu and Debian Power Users~tqw~_darksiderg'
        assert len(torrent.files) == 3
        assert torrent.size == float(3376414.72)
        assert torrent.url == "https://btdigg.org/search?info_hash=c2e018a16bf28520687e400580be08934d00373a"
        dt = torrent.date
        assert dt.year == 2011
        assert dt.month == 2
