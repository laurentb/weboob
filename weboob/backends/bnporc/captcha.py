# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon
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
    def __init__(self, file):
        self.inim = Image.open(file)
        self.nx,self.ny = self.inim.size
        self.inmat = self.inim.load()
        self.map = {}

        self.tiles = [[Tile(x+5*y+1) for y in xrange(5)] for x in xrange(5)]

    def __getitem__(self, (x, y)):
        return self.inmat[x % self.nx, y % self.ny]

    def all_coords(self):
        for y in xrange(self.ny):
            for x in xrange(self.nx):
                yield x, y

    def get_codes(self, code):
        s = ''
        for c in code:
            s += '%02d' % self.map[int(c)].id
        return s

    def build_tiles(self):
        y = 5
        ty = 0
        while y < self.ny:
            x = 6
            tx = 0
            while x < self.nx:
                if self[x,y] == 8:
                    tile = self.tiles[tx][ty]
                    tile.valid = True
                    yy = y
                    while not self[x,yy] in (3,7):
                        l = []
                        tile.map.append(l)
                        xx = x
                        while not self[xx,yy] in (3,7):
                            l.append(self[xx,yy])
                            xx += 1

                        yy += 1

                    self.map[tile.get_num()] = tile

                x += 26
                tx += 1

            y += 25
            ty += 1

class Tile:
    hash = {'b2d25ae11efaaaec6dd6a4c00f0dfc29': 1,
            '600873fa288e75ca6cca092ae95bf129': 2,
            'da24ac28930feee169adcbc9bad4acaf': 3,
            '76294dec2a3c6a7b8d9fcc7a116d1d4f': 4,
            'd9531059e3834b6b8a97e29417a47dec': 5,
            '8ba0c0cfe5e64d6b4afb1aa6f3612c1a': 6,
            '19e0120231e7a9cf4544f96d8c388c8a': 7,
            '83d8ad340156cb7f5c1e64454b66c773': 8,
            '5ee8648d77eeb3e0979f6e59b2fbe66a': 9,
            '3f3fb79bf61ebad096e05287119169df': 0
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
            raise TileError('Tile not found', self)

    def display(self):
        for pxls in self.map:
            for pxl in pxls:
                sys.stdout.write('%02d' % pxl)
            sys.stdout.write('\n')

