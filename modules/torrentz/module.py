# -*- coding: utf-8 -*-

from weboob.capabilities.torrent import CapTorrent
from weboob.tools.backend import Module

from .browser import TorrentzBrowser


__all__ = ['TorrentzModule']


class TorrentzModule(Module, CapTorrent):
    NAME = 'torrentz'
    MAINTAINER = u'Matthieu Weber'
    EMAIL = 'weboob@weber.fi.eu.org'
    VERSION = '2.0'
    DESCRIPTION = 'Torrentz Search Engine.'
    LICENSE = 'AGPL'
    BROWSER = TorrentzBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_torrent(self, id):
        return self.browser.get_torrent(id)

    def get_torrent_file(self, id):
        return self.browser.get_torrent_file(id)

    def iter_torrents(self, pattern):
        return self.browser.iter_torrents(pattern.replace(' ', '+'))
