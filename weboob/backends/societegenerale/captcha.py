# -*- coding: utf-8 -*-

# Copyright(C) 2010  Jocelyn Jaubert
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


import hashlib
import sys
import Image

class TileError(Exception):
    def __init__(self, msg, tile = None):
        Exception.__init__(self, msg)
        self.tile = tile

class Captcha:
    def __init__(self, file, infos):
        self.inim = Image.open(file)
        self.infos = infos
        self.nbr = int(infos["nblignes"])
        self.nbc = int(infos["nbcolonnes"])
        (self.nx,self.ny) = self.inim.size
        self.inmat = self.inim.load()
        self.map = {}

        self.tiles = [[Tile(y * self.nbc + x) for y in xrange(4)] for x in xrange(4)]

    def __getitem__(self, (x, y)):
        return self.inmat[x % self.nx, y % self.ny]

    def all_coords(self):
        for y in xrange(self.ny):
            for x in xrange(self.nx):
                yield x, y

    def get_codes(self, code):
        s = ''
        num = 0
        for c in code:
            index = self.map[int(c)].id
            keycode = self.infos["keyCodes"][num * self.nbr * self.nbc + index]
            s += keycode
            if num < 5:
                s += ','
            num += 1
        return s

    def build_tiles(self):
        for ty in xrange(0, self.nbc):
            y = ty * 23

            for tx in xrange(0, self.nbr):
                x = tx * 24

                tile = self.tiles[tx][ty]

                for yy in xrange(y, y + 23):
                    for xx in xrange(x, x + 24):
                        tile.map.append(self[xx, yy])

                num = tile.get_num()
                if num > -1:
                    tile.valid = True
                    self.map[num] = tile


class Tile:
    hash = {'ff1441b2c5f90703ef04e688e399aca5': 1,
            '53d7f3dfd64f54723b231fc398b6be57': 2,
            '5bcba7fa2107ba9a606e8d0131c162eb': 3,
            '9db6e7ed063e5f9a69ab831e6cc0d721': 4,
            '30ebb75bfa5077f41ccfb72e8c9cc15b': 5,
            '61e27275e494038e524bc9fbbd0be130': 6,
            '0e0816f1b743f320ca561f090df0fbb1': 7,
            '11e7d4a6d447e66a5a112c1d9f7fc442': 8,
            '2ea3c82768030d91571d360acf7a0f75': 9,
            '28a834ebbf0238b46d3fffae1a0b781b': 0,
            '04211db029ce488e07010f618a589c71': -1
           }

    def __init__(self, _id):
        self.id = _id
        self.valid = False
        self.map = []

    def __repr__(self):
        return "<Tile(%02d) valid=%s>" % (self.id, self.valid)

    def checksum(self):
        s = ''
        for pxls in self.map:
            for pxl in pxls:
                s += '%02d' % pxl
        return hashlib.md5(s).hexdigest()

    def get_num(self):
        sum = self.checksum()
        try:
            return self.hash[sum]
        except KeyError:
            self.display()
            raise TileError('Tile not found ' + sum, self)

    def display(self):
        print self.checksum()

