# -*- coding: utf-8 -*-

from weboob.tools.test import BackendTest
from weboob.capabilities.torrent import MagnetOnly
from weboob.tools.date import date

from random import choice


class TorrentzTest(BackendTest):
    MODULE = 'torrentz'

    def test_iter_torrents(self):
        # try something popular so we sometimes get a magnet-only torrent

        l = list(self.backend.iter_torrents('ubuntu linux'))
        self.assertEquals(50, len(l))
        for torrent in l:
            assert torrent.id
            assert torrent.name
            assert not(torrent.size == torrent.size) or torrent.size >= 0
            assert (torrent.date is None or type(torrent.date) is date)
            assert torrent.seeders >= 0
            assert torrent.leechers >= 0

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
        assert len(torrent.files) == 4
        assert torrent.size == float(7010361.0)
        dt = torrent.date
        assert dt.year == 2013
        assert dt.month == 12
