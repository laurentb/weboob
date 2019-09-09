#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright(C) 2017 Matthieu Weber
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import sys


class RboorrentDownload(object):
    def __init__(self, _id, no_tracker):
        self.id, self.backend_name = _id.split("@")
        self.no_tracker = no_tracker
        self.weboob = Weboob()
        self.backend = self.weboob.load_backends(modules=[self.backend_name])[self.backend_name]

    def get_magnet(self, torrent):
        if self.no_tracker:
            return "&".join([_ for _ in torrent.magnet.split("&") if not _.startswith("tr=")])
        else:
            return torrent.magnet

    def write_meta(self, torrent):
        dest = "meta-%s-%s.torrent" % (torrent.id, torrent.name)
        magnet = self.get_magnet(torrent)
        buf = "d10:magnet-uri%d:%se" % (len(magnet), magnet)
        try:
            with open(dest, 'w') as f:
                f.write(buf)
        except IOError as e:
            print('Unable to write "%s": %s' % (dest, e.message))

    def write_torrent(self, torrent):
        dest = "%s-%s.torrent" % (torrent.id, torrent.name)
        try:
            buf = self.backend.get_torrent_file(torrent.id)
            if buf:
                try:
                    with open(dest, 'w') as f:
                        f.write(buf)
                except IOError as e:
                    print('Unable to write "%s": %s' % (dest, e))
        except Exception as e:
            print("Could not get torrent file for %s@%s" % (self.id, self.backend_name))

    def run(self):
        try:
            torrent = self.backend.get_torrent(self.id)
            if torrent.magnet:
                self.write_meta(torrent)
            else:
                self.write_torrent(torrent)
        except HTTPNotFound:
            print("Could not find %s@%s" % (self.id, self.backend_name))


def usage():
    prog_name = sys.argv[0].split("/")[-1]
    print("Usage: %s [-b] HASH@MODULE" % prog_name)
    print("  -b: don't include tracker URLs in the magnet link")
    sys.exit()


def parsed_args():
    if len(sys.argv) == 3 and sys.argv[1] == "-b":
        return (sys.argv[2], True)
    elif len(sys.argv) == 2:
        if sys.argv[1] in ["-h", "--help"]:
            usage()
        else:
            return (sys.argv[1], False)
    else:
        usage()


if __name__ == "__main__":
    args = parsed_args()

    from weboob.core import Weboob
    from weboob.browser.exceptions import HTTPNotFound

    r = RboorrentDownload(*args)
    try:
        r.run()
    except Exception as e:
        print("Error: %s" % e.message)
